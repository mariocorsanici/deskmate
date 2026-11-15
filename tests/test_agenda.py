"""Exercise the real isolated-mode CLI with a separate data root per test."""
import concurrent.futures
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'tools' / 'agenda.py'


class AgendaCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        self.data.mkdir()
        self.script = self.root / 'tools' / 'agenda.py'
        self.script.parent.mkdir()
        if SOURCE.exists():
            shutil.copyfile(SOURCE, self.script)
        self.path = self.data / 'agenda.md'
        self.language('en')

    def language(self, value):
        (self.data / 'config.json').write_text(json.dumps({'language': value}))

    def seed(self, text):
        self.path.write_bytes(text.encode('utf-8') if isinstance(text, str) else text)

    def run_cli(self, *args, rc=0):
        self.assertTrue(self.script.is_file(), 'agenda CLI is not implemented')
        result = subprocess.run([sys.executable, '-I', '-B', str(self.script), *args],
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=15)
        self.assertEqual(result.returncode, rc, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def listing(self, *args, rc=0):
        return json.loads(self.run_cli('list', '--today', '2026-11-06', *args, rc=rc).stdout)

    def test_missing_file_initialized_with_machine_readable_list(self):
        result = self.run_cli('list', '--today', '2026-11-06')
        self.assertEqual(json.loads(result.stdout), {
            'today': [], 'due': [], 'deadline': [], 'undated': 0,
            'upcoming': [], 'closed': []})
        self.assertIn('created', result.stderr)
        self.assertEqual(self.path.read_text(), '# Agenda\n\nNon-development days and tasks. Dates are a reference, not a constraint.\n\n## Days\n\n## Tasks\n')

    def test_every_non_matching_command_initializes_missing_file(self):
        for args in [('add', 'Task'), ('day', '2026-11-06', 'morning', 'Office'),
                     ('archive', '--today', '2026-11-06'), ('is-dev-day', '2026-11-06')]:
            with self.subTest(args=args):
                self.path.unlink(missing_ok=True)
                self.assertIn('created', self.run_cli(*args).stderr)
                self.assertTrue(self.path.is_file())

    def test_italian_keywords_and_closed_dates_are_preserved(self):
        self.language('it')
        self.run_cli('add', 'Report', '--when', '2026-11-13', '--due', '2026-11-20')
        self.run_cli('day', '2026-11-12', 'afternoon', 'Ufficio')
        result = self.run_cli('done', 'report', '--today', '2026-11-06')
        self.assertEqual(result.stdout, '- [x] Report · quando: 2026-11-13 · entro: 2026-11-20 · fatto 2026-11-06\n')
        self.assertIn('## Giorni', self.path.read_text())
        self.assertIn('- 2026-11-12 · pomeriggio · Ufficio', self.path.read_text())

    def test_add_returns_the_written_line(self):
        result = self.run_cli('add', 'Expense report', '--due', '2026-11-30')
        self.assertEqual(result.stdout, '- [ ] Expense report · due: 2026-11-30\n')
        self.assertIn(result.stdout, self.path.read_text())

    def test_add_warns_for_due_before_when_and_weekend(self):
        result = self.run_cli('add', 'Report', '--when', '2026-11-08', '--due', '2026-11-07')
        self.assertIn('before', result.stderr)
        self.assertIn('weekend', result.stderr)

    def test_day_weekend_notice(self):
        self.assertIn('weekend', self.run_cli('day', '2026-11-07', 'day', 'Travel').stderr)

    def test_missing_section_appended_without_rewriting_notes(self):
        raw = b'# My agenda\r\n\r\n## Days\r\n\r\n## Notes\r\nKeep this\r\n'
        self.seed(raw)
        result = self.run_cli('add', 'Task')
        self.assertIn('## Tasks', result.stderr)
        self.assertTrue(self.path.read_bytes().startswith(raw))
        self.assertIn(b'## Tasks\r\n- [ ] Task\r\n', self.path.read_bytes())

    def test_invalid_lines_reported_and_unchanged_while_write_proceeds(self):
        raw = '# Agenda\n\n## Days\nBROKEN DAY\n\n## Tasks\n- [ ] valid\nBROKEN TASK\n'
        self.seed(raw)
        result = self.run_cli('add', 'New', rc=2)
        self.assertIn('agenda.md:4: invalid: BROKEN DAY', result.stderr)
        self.assertIn('agenda.md:8: invalid: BROKEN TASK', result.stderr)
        self.assertEqual(self.path.read_text(), raw + '- [ ] New\n')

    def test_italian_invalid_diagnostic_and_read_only_list(self):
        self.language('it')
        self.seed('# Agenda\n## Giorni\nnon valida\n## Attività\n')
        before = self.path.read_bytes()
        result = self.run_cli('list', rc=2)
        self.assertIn('agenda.md:3: non valida: non valida', result.stderr)
        self.assertEqual(json.loads(result.stdout)['undated'], 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_binary_damage_and_crlf_preserved_on_unrelated_add(self):
        raw = b'# Personal\r\n## Days\r\ninvalid \xff\r\n## Tasks\r\n- [ ] Keep  \r\n\r\n## Notes\r\nEnd'
        self.seed(raw)
        self.run_cli('add', 'New', rc=2)
        self.assertEqual(self.path.read_bytes(), raw.replace(b'\r\n\r\n## Notes', b'\r\n- [ ] New\r\n\r\n## Notes'))

    def test_done_rewrites_only_matched_line_with_crlf(self):
        self.seed(b'# Agenda\r\n## Days\r\n\r\n## Tasks\r\n- [ ] Caff\xc3\xa8\r\n- [ ] Other\r\n## Notes\r\nEnd')
        before = self.path.read_bytes()
        self.run_cli('done', 'CAFFE', '--today', '2026-11-06')
        self.assertEqual(self.path.read_bytes(), before.replace(
            b'- [ ] Caff\xc3\xa8\r\n', b'- [x] Caff\xc3\xa8 \xc2\xb7 done 2026-11-06\r\n'))

    def test_done_without_match_writes_nothing_even_if_sections_missing(self):
        self.seed('# Personal notes\n')
        before = self.path.read_bytes()
        self.run_cli('done', 'missing', rc=1)
        self.assertEqual(self.path.read_bytes(), before)

    def test_done_on_missing_file_does_not_write_on_usage_error(self):
        self.run_cli('done', 'missing', rc=1)
        self.assertFalse(self.path.exists())

    def test_ambiguous_done_prints_candidates_without_writing(self):
        self.seed('# Agenda\n## Days\n## Tasks\n- [ ] Report A\n- [ ] Report B\n')
        before = self.path.read_bytes()
        result = self.run_cli('done', 'report', rc=1)
        self.assertIn('Report A', result.stderr)
        self.assertIn('Report B', result.stderr)
        self.assertEqual(self.path.read_bytes(), before)

    def test_done_ignores_closed_tasks(self):
        self.seed('# Agenda\n## Days\n## Tasks\n- [x] Report old · done 2026-11-01\n- [ ] Report new\n')
        self.assertIn('Report new', self.run_cli('done', 'report', '--today', '2026-11-06').stdout)

    def test_remove_matches_day_or_task_description_case_and_accent_insensitive(self):
        self.run_cli('day', '2026-11-12', 'day', 'Città')
        self.run_cli('add', 'Caffè')
        self.run_cli('done', 'caffe', '--today', '2026-11-06')
        self.run_cli('remove', 'CITTA')
        self.run_cli('remove', 'CAFFE')
        self.assertNotIn('Città', self.path.read_text())
        self.assertNotIn('Caffè', self.path.read_text())

    def test_remove_ambiguous_across_sections_or_no_match_writes_nothing(self):
        self.seed('# Agenda\n## Days\n- 2026-11-12 · day · Report\n## Tasks\n- [ ] Report\n')
        before = self.path.read_bytes()
        for query in ['report', 'missing']:
            with self.subTest(query=query):
                self.run_cli('remove', query, rc=1)
                self.assertEqual(self.path.read_bytes(), before)

    def test_day_half_parts_coexist_and_whole_day_replaces_both(self):
        self.run_cli('day', '2026-11-12', 'morning', 'Office')
        self.run_cli('day', '2026-11-12', 'afternoon', 'Travel')
        self.assertEqual(len(self.listing()['upcoming']), 2)
        result = self.run_cli('day', '2026-11-12', 'day', 'Offsite')
        self.assertIn('replaced', result.stderr)
        self.assertIn('Office', result.stderr)
        self.assertIn('Travel', result.stderr)
        self.assertEqual(self.listing()['upcoming'], ['- 2026-11-12 · day · Offsite'])

    def test_day_half_replaces_whole_and_same_half_only(self):
        self.run_cli('day', '2026-11-12', 'day', 'All day')
        self.run_cli('day', '2026-11-12', 'morning', 'Morning')
        self.run_cli('day', '2026-11-12', 'afternoon', 'Afternoon')
        self.run_cli('day', '2026-11-12', 'morning', 'New morning')
        lines = self.listing()['upcoming']
        self.assertEqual(len(lines), 2)
        self.assertIn('- 2026-11-12 · afternoon · Afternoon', lines)
        self.assertIn('- 2026-11-12 · morning · New morning', lines)

    def test_invalid_dates_and_arguments_leave_agenda_untouched(self):
        self.seed('# Agenda\n## Days\n## Tasks\n')
        before = self.path.read_bytes()
        invalid = [('add', 'Task', '--when', '2026-02-30'),
                   ('add', 'Task', '--due', '2026-2-01'),
                   ('day', '2026-13-01', 'day', 'Travel'),
                   ('day', '2026-11-06', 'giornata', 'Travel'),
                   ('is-dev-day', 'oops'), ('list', '--today', '2026-02-29'),
                   ('archive', '--closed-before', 'invalid'),
                   ('done', 'task', '--today', 'no'), (), ('unknown',)]
        for args in invalid:
            with self.subTest(args=args):
                self.run_cli(*args, rc=1)
                self.assertEqual(self.path.read_bytes(), before)

    def test_unroundtrippable_descriptions_are_usage_errors(self):
        self.seed('# Agenda\n## Days\n## Tasks\n')
        before = self.path.read_bytes()
        for description in ['', '  ', 'first\n- [ ] injected', 'one\rtwo', 'one · when: 2026-11-06']:
            with self.subTest(description=description):
                self.run_cli('add', description, rc=1)
                self.assertEqual(self.path.read_bytes(), before)

    def test_all_line_separators_rejected_before_add_or_day(self):
        before = b'# Agenda\n## Days\n## Tasks\n- [ ] Existing\n'
        for separator in ['\n', '\r', '\r\n', '\v', '\f', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029']:
            text = 'Report' + separator + '- [ ] Injected'
            for args in [('add', text, '--due', '2026-11-06'),
                         ('day', '2026-11-06', 'day', text)]:
                with self.subTest(separator=repr(separator), command=args[0]):
                    self.seed(before)
                    self.run_cli(*args, rc=1)
                    self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_metadata_and_dates_are_not_silently_parsed_as_descriptions(self):
        invalid = ['- [ ] Task · due: tomorrow', '- [ ] Task · when: 2026-02-30',
                   '- [ ] Task · due: 2026-11-06 · when: 2026-11-05',
                   '- [x] Task without completion date', '- [ ] Task · done 2026-11-06',
                   '- 2026-02-30 · day · Travel', '- 2026-11-06 · evening · Travel']
        self.seed('# Agenda\n## Days\n' + '\n'.join(invalid[-2:]) + '\n## Tasks\n' + '\n'.join(invalid[:-2]) + '\n')
        result = self.run_cli('list', rc=2)
        self.assertEqual(result.stderr.count(': invalid:'), 7)
        self.assertEqual(json.loads(result.stdout)['undated'], 0)

    def test_language_change_keeps_existing_entries_readable_and_unchanged(self):
        self.language('it')
        self.run_cli('add', 'Report', '--when', '2026-11-06', '--due', '2026-11-09')
        self.run_cli('day', '2026-11-06', 'day', 'Trasferta')
        before = self.path.read_bytes()
        self.language('en')
        self.run_cli('is-dev-day', '2026-11-06', rc=3)
        listing = self.listing()
        self.assertEqual(listing['due'], ['- [ ] Report · quando: 2026-11-06 · entro: 2026-11-09'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_list_fixed_date_buckets_with_inclusive_workday_boundaries(self):
        self.seed('''# Agenda
## Days
- 2026-11-06 · morning · Office today
- 2026-11-07 · day · Weekend event
- 2026-11-13 · day · Last upcoming day
- 2026-11-16 · day · Outside window
## Tasks
- [ ] Due today · when: 2026-11-06
- [ ] Earlier · when: 2026-11-05
- [ ] Not yet · when: 2026-11-09
- [ ] Deadline boundary · due: 2026-11-11
- [ ] Past deadline · due: 2026-11-01
- [ ] Far deadline · due: 2026-11-12
- [ ] No dates
- [x] Recent · done 2026-11-05
- [x] Older · done 2026-11-01
''')
        listed = self.listing('--closed-since', '2026-11-05')
        self.assertEqual(listed['today'], ['- 2026-11-06 · morning · Office today'])
        self.assertEqual(listed['due'], ['- [ ] Due today · when: 2026-11-06', '- [ ] Earlier · when: 2026-11-05'])
        self.assertEqual(listed['deadline'], ['- [ ] Deadline boundary · due: 2026-11-11', '- [ ] Past deadline · due: 2026-11-01'])
        self.assertEqual(listed['undated'], 1)
        self.assertEqual(listed['upcoming'], ['- 2026-11-07 · day · Weekend event', '- 2026-11-13 · day · Last upcoming day'])
        self.assertEqual(listed['closed'], ['- [x] Recent · done 2026-11-05'])
        self.assertEqual(self.listing()['closed'], [])

    def test_weekend_list_window_counts_weekdays(self):
        self.seed('# Agenda\n## Days\n- 2026-11-13 · day · Friday\n- 2026-11-16 · day · Monday\n## Tasks\n- [ ] Deadline · due: 2026-11-11\n')
        listed = json.loads(self.run_cli('list', '--today', '2026-11-07').stdout)
        self.assertEqual(listed['upcoming'], ['- 2026-11-13 · day · Friday'])
        self.assertEqual(listed['deadline'], ['- [ ] Deadline · due: 2026-11-11'])

    def test_is_dev_day_whole_day_wins_over_invalid_file(self):
        self.seed('# Agenda\n## Days\n- 2026-11-06 · day · Travel\nBROKEN\n## Tasks\n')
        result = self.run_cli('is-dev-day', '2026-11-06', rc=3)
        self.assertIn('invalid: BROKEN', result.stderr)
        self.run_cli('is-dev-day', '2026-11-09', rc=2)

    def test_half_days_and_unlisted_weekends_are_development_days(self):
        self.run_cli('day', '2026-11-06', 'morning', 'Office')
        self.run_cli('day', '2026-11-06', 'afternoon', 'Travel')
        self.run_cli('is-dev-day', '2026-11-06')
        self.run_cli('is-dev-day', '2026-11-07')

    def test_archive_moves_past_days_and_only_requested_closed_tasks(self):
        self.seed('''# Agenda
## Days
- 2026-10-30 · day · October trip
- 2026-11-05 · day · Yesterday trip
- 2026-11-06 · day · Today trip
## Tasks
- [ ] Open · when: 2026-10-01
- [x] Old · when: 2026-09-01 · done 2026-10-30
- [x] Boundary · done 2026-11-01
- [x] Today · done 2026-11-06
''')
        self.run_cli('archive', '--today', '2026-11-06', '--closed-before', '2026-11-01')
        october = (self.data / 'archive' / 'agenda-2026-10.md').read_text()
        november = (self.data / 'archive' / 'agenda-2026-11.md').read_text()
        self.assertIn('October trip', october)
        self.assertIn('done 2026-10-30', october)
        self.assertIn('Yesterday trip', november)
        active = self.path.read_text()
        self.assertNotIn('Yesterday trip', active)
        self.assertNotIn('October trip', active)
        self.assertIn('Today trip', active)
        self.assertIn('- [ ] Open', active)
        self.assertIn('- [x] Boundary', active)
        self.assertIn('- [x] Today', active)

    def test_default_archive_keeps_closed_tasks_and_is_idempotent(self):
        self.seed('# Agenda\n## Days\n- 2026-11-05 · day · Trip\n## Tasks\n- [x] Task · done 2026-10-01\n')
        self.run_cli('archive', '--today', '2026-11-06')
        before = (self.data / 'archive' / 'agenda-2026-11.md').read_bytes()
        self.run_cli('archive', '--today', '2026-11-06')
        self.assertIn('- [x] Task', self.path.read_text())
        self.assertEqual((self.data / 'archive' / 'agenda-2026-11.md').read_bytes(), before)

    def test_archive_preserves_invalid_lines_and_unrelated_bytes(self):
        raw = '# Agenda\r\n## Days\r\nBAD DAY\r\n- 2026-11-05 · day · Trip\r\n## Tasks\r\nBAD TASK\r\n## Notes\r\nUnchanged'
        self.seed(raw)
        self.run_cli('archive', '--today', '2026-11-06', rc=2)
        self.assertEqual(self.path.read_bytes(), raw.replace('- 2026-11-05 · day · Trip\r\n', '').encode())

    def test_archive_appends_without_rewriting_existing_archive_notes(self):
        archive = self.data / 'archive' / 'agenda-2026-11.md'
        archive.parent.mkdir()
        before = b'# Personal archive\r\n## Days\r\n\r\n## Tasks\r\n\r\n## Notes\r\nRetain'
        archive.write_bytes(before)
        self.run_cli('day', '2026-11-05', 'day', 'Trip')
        self.run_cli('archive', '--today', '2026-11-06')
        self.assertEqual(archive.read_bytes(), before.replace(b'\r\n## Tasks', b'- 2026-11-05 \xc2\xb7 day \xc2\xb7 Trip\r\n\r\n## Tasks'))

    def test_archiving_does_not_forget_historical_non_development_days(self):
        self.run_cli('day', '2026-10-30', 'day', 'Trip')
        self.run_cli('archive', '--today', '2026-11-06')
        self.run_cli('is-dev-day', '2026-10-30', rc=3)
        self.run_cli('is-dev-day', '2026-10-29')

    def test_repeated_list_initialization_preserves_existing_agenda_bytes(self):
        self.seed(b'# Custom\r\n## Days\r\n\r\n## Tasks\r\n- [ ] Retain\r\n')
        before = self.path.read_bytes()
        self.run_cli('list')
        self.run_cli('list')
        self.assertEqual(self.path.read_bytes(), before)

    def test_exclusive_lock_blocks_writer_until_released(self):
        self.assertTrue(self.script.is_file(), 'agenda CLI is not implemented')
        with (self.data / '.agenda.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            process = subprocess.Popen([sys.executable, '-I', '-B', str(self.script), 'add', 'Blocked'],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    process.communicate(timeout=0.25)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
                out, err = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, out + err)
        self.assertIn('Blocked', self.path.read_text())

    def test_concurrent_initialization_and_additions_do_not_lose_entries(self):
        self.assertTrue(self.script.is_file(), 'agenda CLI is not implemented')
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda n: self.run_cli('add', f'Task {n}'), range(20)))
        self.assertEqual(len(results), 20)
        self.assertEqual(self.listing()['undated'], 20)
        content = self.path.read_text()
        for n in range(20):
            self.assertEqual(content.count(f'- [ ] Task {n}\n'), 1)


if __name__ == '__main__':
    unittest.main()
