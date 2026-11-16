"""goal and switch rows (Daily loop L06, L07) keep their text as written."""
import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DailyEvents(unittest.TestCase):
    def logged(self, *args):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, 'DESKMATE_DATA_DIR': tmp, 'PYTHONDONTWRITEBYTECODE': '1'}
            subprocess.run([sys.executable, '-I', str(ROOT / 'bin/deskmate'), 'log-event', *args],
                           env=env, check=True, capture_output=True)
            with (Path(tmp) / 'log.csv').open(encoding='utf-8', newline='') as stream:
                return list(csv.DictReader(stream))

    def test_goal_text_with_commas_and_quotes_is_kept(self):
        text = 'today the "Cam5" demo matters, because Gio ships it Friday'
        row = self.logged('goal', text, 'sess', '/work', '--provider', 'codex')[-1]
        self.assertEqual((row['event'], row['detail'], row['session'], row['cwd'], row['provider']),
                         ('goal', text, 'sess', '/work', 'codex'))
        self.assertEqual(row['usage_scope'], '')

    def test_switch_without_session_keeps_arrow_and_reason(self):
        text = 'vlm → basler: waiting for the CI run, 20 minutes'
        row = self.logged('switch', text)[-1]
        self.assertEqual((row['event'], row['detail'], row['session']), ('switch', text, ''))


if __name__ == '__main__':
    unittest.main()
