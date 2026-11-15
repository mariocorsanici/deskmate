"""retro_due.py: a retrospective every two development days (Daily loop L05, Agenda A06)."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ['date', 'time', 'weekday', 'event', 'detail', 'session', 'cwd',
           'turns', 'input_tokens', 'cache_tokens', 'output_tokens', 'usage_scope']


class RetroDue(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'tools').mkdir()
        (self.root / 'data').mkdir()
        for name in ('retro_due.py', 'usage_log.py', 'agenda.py'):
            if (ROOT / 'tools' / name).exists():
                shutil.copyfile(ROOT / 'tools' / name, self.root / 'tools' / name)
        (self.root / 'data' / 'config.json').write_text('{"language": "en"}')

    def log(self, *rows):
        with (self.root / 'data' / 'log.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            for date, event in rows:
                writer.writerow({**dict.fromkeys(COLUMNS, ''), 'date': date, 'time': '10:00', 'event': event})

    def agenda(self, text):
        (self.root / 'data' / 'agenda.md').write_text(text, encoding='utf-8')

    def due(self, today, rc=0):
        env = {k: v for k, v in os.environ.items() if k != 'DESKMATE_DATA_DIR'}
        result = subprocess.run([sys.executable, '-I', '-B', str(self.root / 'tools' / 'retro_due.py'),
                                 '--today', today], capture_output=True, text=True, env=env, timeout=15)
        self.assertEqual(result.returncode, rc, result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return json.loads(result.stdout) if rc == 0 else result

    # L05

    def test_two_development_days_since_the_last_retrospective_make_it_due(self):
        self.log(('2026-11-06', 'how-did-it-go'), ('2026-11-09', 'checkpoint'), ('2026-11-10', 'call-it-a-day'))
        out = self.due('2026-11-11')
        self.assertEqual(out['last_retrospective'], '2026-11-06')
        self.assertEqual(out['development_days'], ['2026-11-09', '2026-11-10'])
        self.assertTrue(out['due'])

    def test_one_development_day_is_not_enough(self):
        self.log(('2026-11-06', 'how-did-it-go'), ('2026-11-09', 'checkpoint'), ('2026-11-09', 'checkpoint'))
        out = self.due('2026-11-10')
        self.assertEqual(out['development_days'], ['2026-11-09'])
        self.assertFalse(out['due'])

    def test_only_checkpoint_and_call_it_a_day_starts_count(self):
        self.log(('2026-11-06', 'how-did-it-go'), ('2026-11-09', 'morning-reminder'),
                 ('2026-11-09', 'whats-on-today'), ('2026-11-10', 'checkpoint-end'),
                 ('2026-11-10', 'study-later'))
        self.assertEqual(self.due('2026-11-11')['development_days'], [])

    def test_the_retrospective_day_and_today_do_not_count(self):
        self.log(('2026-11-09', 'checkpoint'), ('2026-11-09', 'how-did-it-go'),
                 ('2026-11-10', 'checkpoint'), ('2026-11-11', 'checkpoint'))
        self.assertEqual(self.due('2026-11-11')['development_days'], ['2026-11-10'])

    def test_without_any_retrospective_every_development_day_counts(self):
        self.log(('2026-11-02', 'checkpoint'), ('2026-11-03', 'checkpoint'))
        out = self.due('2026-11-04')
        self.assertIsNone(out['last_retrospective'])
        self.assertTrue(out['due'])

    def test_missing_log_is_reported_not_due(self):
        out = self.due('2026-11-04')
        self.assertFalse(out['log_found'])
        self.assertFalse(out['due'])

    def test_unrecognized_log_fails_without_traceback(self):
        (self.root / 'data' / 'log.csv').write_text('nonsense,header\n1,2\n')
        result = self.due('2026-11-04', rc=1)
        self.assertIn('log.csv', result.stderr)

    # A06

    def test_whole_non_development_day_is_excluded_and_named(self):
        self.log(('2026-11-06', 'how-did-it-go'), ('2026-11-09', 'checkpoint'),
                 ('2026-11-10', 'checkpoint'))
        self.agenda('# Agenda\n\n## Days\n- 2026-11-10 · day · Trasferta Monfalcone\n\n## Tasks\n')
        out = self.due('2026-11-11')
        self.assertEqual(out['development_days'], ['2026-11-09'])
        self.assertEqual(out['non_development_days'],
                         [{'date': '2026-11-10', 'entry': '- 2026-11-10 · day · Trasferta Monfalcone'}])
        self.assertFalse(out['due'])

    def test_half_day_still_counts(self):
        self.log(('2026-11-06', 'how-did-it-go'), ('2026-11-09', 'checkpoint'),
                 ('2026-11-10', 'checkpoint'))
        self.agenda('# Agenda\n\n## Days\n- 2026-11-10 · morning · Ufficio Trieste\n\n## Tasks\n')
        self.assertTrue(self.due('2026-11-11')['due'])

    def test_archived_non_development_day_is_excluded(self):
        self.log(('2026-11-06', 'how-did-it-go'), ('2026-11-09', 'checkpoint'),
                 ('2026-11-10', 'checkpoint'))
        self.agenda('# Agenda\n\n## Days\n\n## Tasks\n')
        (self.root / 'data' / 'archive').mkdir()
        (self.root / 'data' / 'archive' / 'agenda-2026-11.md').write_text(
            '# Agenda\n\n## Days\n- 2026-11-10 · day · Trasferta Monfalcone\n\n## Tasks\n', encoding='utf-8')
        self.assertEqual(self.due('2026-11-11')['development_days'], ['2026-11-09'])

    def test_non_development_days_without_work_are_listed_in_the_period(self):
        self.log(('2026-11-06', 'how-did-it-go'), ('2026-11-09', 'checkpoint'))
        self.agenda('# Agenda\n\n## Days\n- 2026-11-10 · day · Ferie\n\n## Tasks\n')
        out = self.due('2026-11-11')
        self.assertEqual([d['date'] for d in out['non_development_days']], ['2026-11-10'])


if __name__ == '__main__':
    unittest.main()
