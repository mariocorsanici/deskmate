import csv
from datetime import datetime
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ['date', 'time', 'weekday', 'event', 'detail', 'session', 'cwd',
          'turns', 'input_tokens', 'cache_tokens', 'output_tokens']


class ActivityLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / 'data'
        self.data.mkdir()
        self.log = self.data / 'log.csv'
        self.env = {**os.environ, 'DESKMATE_DATA_DIR': str(self.data), 'PYTHONDONTWRITEBYTECODE': '1'}

    def seed(self, extra=()):
        fields = LEGACY + list(extra)
        value = dict.fromkeys(fields, '')
        value.update(date='2026-11-06', time='10:00', event='checkpoint',
                     session='one', cwd='/project', detail='old detail', input_tokens='99')
        for key in extra:
            value[key] = {'provider': 'claude', 'schema_version': '1'}.get(key, 'preserved')
        with self.log.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow(value)

    def records(self):
        with self.log.open(newline='') as stream:
            reader = csv.DictReader(stream)
            values = list(reader)
            self.assertTrue(all(None not in r and None not in r.values() for r in values))
            return reader.fieldnames, values

    def log_args(self, event='checkpoint-end'):
        return ['/bin/zsh', str(ROOT / 'tools/log_event.sh'), event, '', 'one', '/project']

    def run_event(self, event='checkpoint-end'):
        return subprocess.run(self.log_args(event), env=self.env, capture_output=True, text=True, check=True)

    def test_logger_upgrades_legacy_header_and_keeps_history(self):
        self.seed()
        self.run_event()
        fields, rows = self.records()
        self.assertIn('usage_scope', fields)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['input_tokens'], '99')
        self.assertEqual(rows[0]['detail'], 'old detail')
        stamp = datetime.fromisoformat(rows[1]['detail'].replace('Z', '+00:00'))
        self.assertIsNotNone(stamp.tzinfo)
        self.assertIn('.', rows[1]['detail'])

    def test_logger_preserves_provider_and_unknown_columns(self):
        self.seed(('schema_version', 'provider', 'custom'))
        self.run_event('resume-rating')
        fields, rows = self.records()
        self.assertEqual(rows[0]['custom'], 'preserved')
        self.assertEqual(rows[0]['provider'], 'claude')
        self.assertEqual(rows[1]['detail'], '')

    def test_usage_update_preserves_extension_columns_and_legacy_totals_when_missing(self):
        self.seed(('schema_version', 'provider', 'custom'))
        projects = Path(self.tmp.name) / 'projects'
        projects.mkdir()
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'tools/token_usage.py'),
                                 '--projects', str(projects)], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        fields, rows = self.records()
        self.assertIn('usage_scope', fields)
        self.assertEqual(rows[0]['custom'], 'preserved')
        self.assertEqual(rows[0]['input_tokens'], '99')
        self.assertEqual(rows[0]['usage_scope'], 'legacy-window')

    def test_concurrent_append_and_recompute_share_lock(self):
        self.seed(('custom',))
        processes = []
        with (self.data / '.log.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            before = self.log.read_bytes()
            projects = Path(self.tmp.name) / 'projects'
            projects.mkdir()
            commands = [self.log_args('study-later') for _ in range(4)]
            commands.append([sys.executable, '-I', str(ROOT / 'tools/token_usage.py'), '--projects', str(projects)])
            for cmd in commands:
                processes.append(subprocess.Popen(cmd, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            try:
                time.sleep(0.15)
                self.assertTrue(all(p.poll() is None for p in processes))
                self.assertEqual(self.log.read_bytes(), before)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
                for process in processes:
                    out, err = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, out + err)
        _, rows = self.records()
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]['custom'], 'preserved')

    def test_invalid_csv_is_not_replaced(self):
        self.log.write_text('date,event\n2026-11-06,checkpoint,extra\n')
        before = self.log.read_bytes()
        result = subprocess.run(self.log_args(), env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.log.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
