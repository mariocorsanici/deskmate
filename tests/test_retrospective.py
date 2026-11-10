"""Progressive retrospective scenarios using the public CLI and synthetic native stores."""
from contextlib import closing
import csv
import datetime as dt
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SINCE = '2026-11-06'
STAMP = SINCE + 'T10:00:00Z'


class RetrospectiveTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.data = self.home / 'data'
        self.data.mkdir()
        self.project = self.home / 'project'
        self.project.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home), 'CODEX_HOME': str(self.home / '.codex'),
                    'DESKMATE_DATA_DIR': str(self.data), 'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1'}
        (self.data / 'config.json').write_text(json.dumps({'session_delta': {
            'max_messages': 2, 'max_characters': 20}}))

    def invoke(self, *args):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'bin/deskmate'), '--json',
                                 'retrospective', '--since', SINCE, *args], env=self.env,
                                capture_output=True, text=True, timeout=15)
        envelope = json.loads(result.stdout)
        self.assertNotIn('Traceback', envelope['stderr'])
        return result.returncode, envelope

    def report(self, *args):
        code, envelope = self.invoke('--format', 'json', *args)
        self.assertEqual(code, 0, envelope)
        return json.loads(envelope['stdout'])

    def claude(self, sid='same', texts=('saved', 'before checkpoint', 'new work')):
        directory = self.home / '.claude/projects/demo'
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (sid + '.jsonl')
        rows = [{'type': 'user' if i % 2 == 0 else 'assistant', 'cwd': str(self.project),
                 'timestamp': f'{SINCE}T10:0{i}:00Z', 'message': {'content': text}}
                for i, text in enumerate(texts)]
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        index = directory / 'sessions-index.json'
        entries = json.loads(index.read_text())['entries'] if index.exists() else []
        entries.append({'sessionId': sid, 'projectPath': str(self.project), 'created': STAMP,
                        'modified': SINCE + 'T10:10:00Z', 'firstPrompt': 'CANARY private preview'})
        index.write_text(json.dumps({'entries': entries}))
        return path

    def codex(self, sid='same'):
        home = self.home / '.codex'
        home.mkdir(exist_ok=True)
        with closing(sqlite3.connect(home / 'state_5.sqlite')) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS threads (id TEXT, cwd TEXT, created_at INTEGER, '
                       'updated_at INTEGER, rollout_path TEXT, tokens_used INTEGER, history_mode TEXT)')
            db.execute('INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (sid, str(self.project), 1793959200, 1793959320, '', 450, 'paginated'))
        with closing(sqlite3.connect(home / 'thread_history_1.sqlite')) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS thread_items (thread_id TEXT, rollout_ordinal INTEGER, '
                       'created_at_ms INTEGER, item_json TEXT, item_type TEXT)')
            for i, text in enumerate(('saved', 'before checkpoint', 'codex new work')):
                db.execute('INSERT INTO thread_items VALUES (?, ?, ?, ?, ?)',
                           (sid, i, 1793959200000 + i * 60000,
                            json.dumps({'type': 'userMessage', 'content': [{'type': 'text', 'text': text}]}),
                            'userMessage'))

    def card(self, provider='claude', sid='same'):
        source = self.home / 'card.md'
        source.write_text('# Project\n\n## Status\nCheckpoint 2026-11-06T10:01:00Z, '
                          f'session `{sid}`\nPending owner reply.\n')
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'bin/deskmate'), 'card', 'write',
                                 str(self.project), '--expected-revision', '0', '--provider', provider,
                                 '--session-id', sid, '--from', str(source)], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def log(self, provider='claude', sid='logged', date=SINCE, event='checkpoint'):
        path = self.data / 'log.csv'
        fields = ['date', 'time', 'weekday', 'event', 'detail', 'session', 'cwd', 'turns',
                  'input_tokens', 'cache_tokens', 'output_tokens', 'schema_version', 'provider']
        fresh = not path.exists()
        with path.open('a', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            if fresh:
                writer.writeheader()
            writer.writerow(dict.fromkeys(fields, '') | {'date': date, 'time': '10:00',
                'event': event, 'session': sid, 'cwd': str(self.project),
                'provider': provider, 'schema_version': '1'})

    def snapshot(self):
        return {str(p.relative_to(self.home)): p.read_bytes()
                for p in self.home.rglob('*') if p.is_file()}

    def test_initial_view_collects_durable_state_and_both_provider_identities_without_messages(self):
        self.claude(texts=('CANARY conversation',))
        self.codex()
        self.card()
        self.log()
        (self.data / 'handoff.md').write_text('# 2026-11-06\nFinish the migration.\n')
        archive = self.data / 'archive'
        archive.mkdir()
        (archive / 'handoff-2026-11-06.md').write_text('Previous plan in period')
        (archive / 'handoff-2026-10-01.md').write_text('OLD OUTSIDE PERIOD')
        before = self.snapshot()
        result = self.report()
        self.assertEqual({(c['provider'], c['id']) for c in result['candidates']},
                         {('claude', 'same'), ('codex', 'same'), ('claude', 'logged')})
        self.assertEqual(result['selected'], [])
        self.assertEqual(result['deltas'], [])
        self.assertEqual(result['phase'], 'selection')
        self.assertIn('Pending owner reply', json.dumps(result['durable']['cards']))
        self.assertIn('Finish the migration', json.dumps(result['durable']['handoffs']))
        self.assertIn('Previous plan in period', json.dumps(result['durable']['handoffs']))
        self.assertNotIn('OLD OUTSIDE PERIOD', json.dumps(result))
        self.assertNotIn('CANARY', json.dumps(result))
        self.assertEqual(self.snapshot(), before)

    def test_all_candidates_remain_visible_while_recommendations_stop_at_five_with_reasons(self):
        for i in range(8):
            self.claude(sid=f'candidate-{i}')
        result = self.report()
        self.assertEqual(len(result['candidates']), 8)
        self.assertEqual(len(result['recommendations']), 5)
        self.assertTrue(all(r['reasons'] for r in result['recommendations']))
        self.assertEqual(result['deltas'], [])

    def test_selection_replaces_recommendations_and_reads_only_selected_provider_delta(self):
        self.claude(texts=('CANARY unselected conversation',))
        self.codex()
        self.card('codex')
        before = self.snapshot()
        result = self.report('--select', 'codex:same')
        self.assertEqual(result['selected'], ['codex:same'])
        self.assertEqual(len(result['deltas']), 1)
        delta = result['deltas'][0]
        self.assertEqual((delta['provider'], delta['id']), ('codex', 'same'))
        self.assertEqual([m['text'] for m in delta['messages']], ['codex new work'])
        self.assertEqual(delta['limits'], {'max_messages': 2, 'max_characters': 20})
        self.assertNotIn('CANARY', json.dumps(result))
        self.assertEqual(self.snapshot(), before)

    def test_selection_can_add_remove_replace_and_deduplicate_without_a_five_session_limit(self):
        for i in range(7):
            self.claude(sid=f'candidate-{i}')
        result = self.report(*[arg for i in range(7) for arg in ('--select', f'claude:candidate-{i}')],
                             '--select', 'claude:candidate-0')
        self.assertEqual(len(result['selected']), 7)
        self.assertEqual(len(result['deltas']), 7)
        replacement = self.report('--select', 'claude:candidate-6')
        self.assertEqual(replacement['selected'], ['claude:candidate-6'])
        self.assertEqual(len(replacement['deltas']), 1)
        self.assertEqual(self.report()['deltas'], [])

    def test_deepening_is_one_session_with_an_explicit_nonpersistent_override(self):
        self.claude(texts=('first', 'middle', 'last'))
        before = (self.data / 'config.json').read_bytes()
        deeper = self.report('--deepen', 'claude:same', '--max-messages', '3', '--max-characters', '40')
        self.assertEqual([m['text'] for m in deeper['deltas'][0]['messages']], ['first', 'middle', 'last'])
        self.assertEqual(deeper['phase'], 'deepening')
        normal = self.report('--select', 'claude:same')
        self.assertEqual(len(normal['deltas'][0]['messages']), 2)
        self.assertEqual((self.data / 'config.json').read_bytes(), before)
        for args in [('--deepen', 'claude:same'),
                     ('--max-messages', '3'),
                     ('--deepen', 'claude:same', '--max-messages', '0'),
                     ('--deepen', 'claude:same', '--max-messages', '3', '--select', 'claude:same'),
                     ('--deepen', 'claude:same', '--deepen', 'claude:same', '--max-messages', '3')]:
            with self.subTest(args=args):
                code, envelope = self.invoke(*args)
                self.assertEqual(code, 2, envelope)

    def test_missing_transcript_degrades_only_affected_session(self):
        self.claude()
        self.log('codex', 'missing')
        result = self.report('--select', 'codex:missing', '--select', 'claude:same')
        missing, available = result['deltas']
        self.assertEqual(missing['status'], 'degraded')
        self.assertEqual(missing['coverage']['status'], 'unavailable')
        self.assertTrue(missing['warnings'])
        self.assertEqual(available['status'], 'ok')
        self.assertTrue(available['messages'])

    def test_cached_native_metrics_stay_separate_without_refreshing_transcripts(self):
        self.claude()
        self.codex()
        usage = self.data / 'usage'
        usage.mkdir()
        (usage / 'claude.json').write_text(json.dumps({'schema_version': 1, 'provider': 'claude',
            'sessions': {'same': {'provider': 'claude', 'id': 'same', 'cwd': str(self.project),
                'start': STAMP, 'end': STAMP, 'usage': {'input_tokens': 17, 'cache_read_input_tokens': 11},
                'status': 'ok', 'warnings': []}}}))
        result = self.report()
        self.assertEqual(result['metrics']['providers']['claude']['sessions'][0]['usage'],
                         {'input_tokens': 17, 'cache_read_input_tokens': 11})
        self.assertEqual(result['metrics']['providers']['codex']['sessions'][0]['usage'], {'tokens_used': 450})
        self.assertEqual(result['metrics']['usage_source'], 'metadata-and-cached-snapshots')

    def test_invalid_selection_is_rejected_before_any_transcript_is_read(self):
        self.claude()
        for args in [('--select', 'same'), ('--select', 'other:same'),
                     ('--select', 'claude:absent'), ('--since', 'not-a-date')]:
            with self.subTest(args=args):
                code, envelope = self.invoke(*args)
                self.assertEqual(code, 2, envelope)
                self.assertNotIn('messages', envelope['stdout'])

    def test_initial_view_never_calls_conversation_or_usage_readers(self):
        self.claude()
        self.codex()
        code = (
            'import json,sys\n'
            'sys.path.insert(0,sys.argv[1])\n'
            'import retrospective,adapter_claude,adapter_codex\n'
            'def forbidden(*args,**kwargs):\n'
            '    raise AssertionError("conversation reader entered before selection")\n'
            'for adapter in (adapter_claude,adapter_codex):\n'
            '    adapter.read_session=adapter.read_delta=adapter.read_usage=forbidden\n'
            'print(json.dumps(retrospective.report("2026-11-06")))\n')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(ROOT / 'tools')],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload['candidates']), 2)
        self.assertEqual(payload['deltas'], [])

    def test_old_cached_usage_preserves_newer_native_activity_metadata(self):
        self.claude()
        usage = self.data / 'usage'
        usage.mkdir()
        (usage / 'claude.json').write_text(json.dumps({'schema_version': 1, 'provider': 'claude',
            'sessions': {'same': {'provider': 'claude', 'id': 'same', 'cwd': '/old/path',
                'start': '2026-11-01T10:00:00Z', 'end': '2026-11-01T11:00:00Z',
                'usage': {'input_tokens': 17}, 'status': 'ok', 'warnings': []}}}))
        result = self.report()
        candidate = result['candidates'][0]
        self.assertEqual(candidate['end'], '2026-11-06T10:10:00Z')
        self.assertEqual(candidate['cwd'], str(self.project))
        self.assertEqual(candidate['usage'], {'input_tokens': 17})
        self.assertEqual(candidate['usage_as_of'], '2026-11-01T11:00:00Z')

    def test_corrupt_usage_or_one_adapter_failure_keeps_other_candidates_available(self):
        self.claude()
        self.log('codex', 'durable-only')
        usage = self.data / 'usage'
        usage.mkdir()
        (usage / 'codex.json').write_text('{bad snapshot')
        home = self.home / '.codex'
        home.mkdir()
        (home / 'state_5.sqlite').write_bytes(b'unsupported native database')
        result = self.report('--select', 'claude:same')
        self.assertEqual({c['key'] for c in result['candidates']}, {'claude:same', 'codex:durable-only'})
        self.assertTrue(result['deltas'][0]['messages'])
        self.assertTrue(result['warnings'])

    def test_malformed_cached_metadata_degrades_snapshot_without_losing_healthy_evidence(self):
        self.claude()
        self.codex()
        usage = self.data / 'usage'
        usage.mkdir()
        for bad in ({'warnings': None}, {'end': 123}, {'cwd': []}, {'status': {}}):
            with self.subTest(bad=bad):
                record = {'provider': 'claude', 'id': 'same', 'cwd': str(self.project),
                          'start': STAMP, 'end': STAMP, 'usage': {'input_tokens': 17},
                          'status': 'ok', 'warnings': []}
                record.update(bad)
                (usage / 'claude.json').write_text(json.dumps({'schema_version': 1,
                    'provider': 'claude', 'sessions': {'same': record}}))
                result = self.report()
                self.assertEqual({c['key'] for c in result['candidates']}, {'claude:same', 'codex:same'})
                self.assertEqual(result['metrics']['providers']['codex']['sessions'][0]['usage'],
                                 {'tokens_used': 450})
                self.assertTrue(result['warnings'])

    def test_noncanonical_dates_are_rejected_instead_of_silently_dropping_activity(self):
        self.log()
        for value in ('20261106', '2026-W45-5'):
            with self.subTest(value=value):
                code, envelope = self.invoke('--since', value)
                self.assertEqual(code, 2, envelope)

    def test_initial_view_does_not_clean_up_transfer_bundles(self):
        self.claude()
        transfers = self.data / 'transfers'
        transfers.mkdir()
        expired = transfers / 'unrelated.json'
        expired.write_text('leave untouched')
        before = self.snapshot()
        self.report()
        self.assertEqual(self.snapshot(), before)

    def test_empty_store_text_view_is_actionable_and_does_not_create_files(self):
        before = self.snapshot()
        code, result = self.invoke()
        self.assertEqual(code, 0, result)
        self.assertIn('Candidates', result['stdout'])
        self.assertIn('--select', result['stdout'])
        self.assertIn('claude', result['stdout'])
        self.assertIn('codex', result['stdout'])
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
