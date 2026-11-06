import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('token_usage', ROOT / 'tools/token_usage.py')
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


def row(event, detail='', session='one', cwd='/project'):
    value = dict.fromkeys(usage.COLUMNS, '')
    value.update(date='2026-11-06', time='10:00', weekday='fri', event=event,
                 detail=detail, session=session, cwd=cwd)
    return value


def command(second, name='checkpoint'):
    return {'type': 'user', 'timestamp': f'2026-11-06T10:00:{second:02d}Z',
            'message': {'content': f'<command-name>/{name}</command-name>'}}


def answer(second, amount=2, identity=None):
    return {'type': 'assistant', 'timestamp': f'2026-11-06T10:00:{second:02d}Z',
            'message': {'id': identity or f'a-{second}', 'usage': {
                'input_tokens': amount, 'cache_creation_input_tokens': 1,
                'cache_read_input_tokens': 3, 'output_tokens': 5}, 'content': []}}


class UsageWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.projects = Path(self.tmp.name) / 'projects'
        self.transcript = self.projects / 'project/one.jsonl'
        self.transcript.parent.mkdir(parents=True)
        self.patch = patch.object(usage, 'PROJECTS', self.projects)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def compute(self, records, rows):
        self.transcript.write_text(''.join(json.dumps(r) + '\n' for r in records))
        usage.compute('one', rows)
        return rows

    def test_marker_excludes_unrelated_work(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:02.123456+00:00')]
        self.compute([command(0), answer(1), answer(3, 100)], rows)
        self.assertEqual(rows[0]['input_tokens'], '3')
        self.assertEqual(rows[0]['turns'], '1')
        self.assertEqual(rows[0].get('usage_scope'), 'end-marked')
        self.assertEqual(rows[1]['input_tokens'], '')

    def test_no_marker_keeps_legacy_window(self):
        rows = [row('checkpoint')]
        self.compute([command(0), answer(1), answer(3, 100)], rows)
        self.assertEqual(rows[0]['input_tokens'], '104')
        self.assertEqual(rows[0].get('usage_scope'), 'legacy-window')

    def test_two_skills_in_sequence(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:02Z'),
                row('study-later'), row('study-later-end', '2026-11-06T10:00:05Z')]
        self.compute([command(0), answer(1), command(3, 'study-later'), answer(4, 7), answer(6, 100)], rows)
        self.assertEqual([rows[i]['input_tokens'] for i in (0, 2)], ['3', '8'])
        self.assertEqual([rows[i].get('usage_scope') for i in (0, 2)], ['end-marked', 'end-marked'])

    def test_repeated_skill_in_same_minute(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:02Z'),
                row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:05Z')]
        self.compute([command(0), answer(1), command(3), answer(4, 7), answer(6, 100)], rows)
        self.assertEqual([rows[i]['input_tokens'] for i in (0, 2)], ['3', '8'])

    def test_missing_first_marker_does_not_borrow_next_run_marker(self):
        rows = [row('checkpoint'), row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:05Z')]
        self.compute([command(0), answer(1), command(3), answer(4), answer(6, 100)], rows)
        self.assertEqual(rows[0].get('usage_scope'), 'legacy-window')
        self.assertEqual(rows[1].get('usage_scope'), 'end-marked')
        self.assertEqual(rows[1]['turns'], '1')

    def test_next_command_precedes_late_marker(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:05Z')]
        self.compute([command(0), answer(1), command(3, 'help'), answer(4)], rows)
        self.assertEqual(rows[0]['turns'], '1')
        self.assertEqual(rows[0].get('usage_scope'), 'legacy-window')

    def test_other_session_marker_cannot_close_run(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:02Z', session='two')]
        self.compute([command(0), answer(1), answer(3)], rows)
        self.assertEqual(rows[0]['turns'], '2')
        self.assertEqual(rows[0].get('usage_scope'), 'legacy-window')

    def test_wrong_folder_marker_cannot_close_run(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:02Z', cwd='/other')]
        self.compute([command(0), answer(1), answer(3)], rows)
        self.assertEqual(rows[0]['turns'], '2')
        self.assertEqual(rows[0].get('usage_scope'), 'legacy-window')

    def test_invalid_or_early_markers_are_legacy(self):
        for stamp in ('invalid', '', '2026-11-06T10:00:02', '2026-11-06T09:59:59Z'):
            with self.subTest(stamp=stamp):
                rows = [row('checkpoint'), row('checkpoint-end', stamp)]
                self.compute([command(0), answer(1), answer(3)], rows)
                self.assertEqual(rows[0].get('usage_scope'), 'legacy-window')
                self.assertEqual(rows[0]['turns'], '2')

    def test_timezone_offsets_are_normalized(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T11:00:02+01:00')]
        self.compute([command(0), answer(1), answer(3)], rows)
        self.assertEqual(rows[0]['turns'], '1')
        self.assertEqual(rows[0].get('usage_scope'), 'end-marked')

    def test_usage_deduplicates_native_message_id(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:04Z')]
        self.compute([command(0), answer(1, identity='same'), answer(2, identity='same')], rows)
        self.assertEqual(rows[0]['turns'], '1')
        self.assertEqual(rows[0].get('usage_scope'), 'end-marked')

    def test_malformed_records_do_not_break_valid_window(self):
        rows = [row('checkpoint'), row('checkpoint-end', '2026-11-06T10:00:04Z')]
        self.compute([None, {'type': 'assistant', 'message': 'invalid'},
                      command(0), answer(1), {'type': 'assistant', 'timestamp': None}], rows)
        self.assertEqual(rows[0]['turns'], '1')


if __name__ == '__main__':
    unittest.main()
