"""Reminder behavior through the CLI and scripts, with no native notifications."""
import csv
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RemindersTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.data = self.home / 'data'
        self.data.mkdir()
        self.executables = self.home / 'bin'
        self.executables.mkdir()
        # Freeze only the clock in the reminder process. The public shell script
        # and real reminder command run unchanged; no production test switch.
        self.clock = self.home / 'clock'
        self.clock.write_text('2026-11-16T09:10:00')  # Monday
        python = self.executables / 'python3'
        python.write_text('#!' + sys.executable + '\n' + f'''import csv, datetime as dt, os, pathlib, sys
args = [arg for arg in sys.argv[1:] if arg not in ('-I', '-B')]
if len(args) > 1 and args[1] == 'reminders':
    frozen = dt.datetime.fromisoformat((pathlib.Path(os.environ['HOME']) / 'clock').read_text())
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen if tz is None else frozen.astimezone(tz)
    class Date(dt.date):
        @classmethod
        def today(cls):
            return frozen.date()
    dt.datetime, dt.date = Clock, Date
    sys.path.insert(0, {str(ROOT / 'tools')!r})
    import reminders
    sys.argv = [str(pathlib.Path(args[0]).parent.parent / 'tools/reminders.py'), *args[2:]]
    try:
        reminders.main()
    except (OSError, ValueError, csv.Error) as error:
        print(error, file=sys.stderr)
        sys.exit(2)
else:
    os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])
''')
        python.chmod(0o755)
        # Always replace the desktop boundary, even in dry-run tests.
        self.executable('osascript', 'printf "%s" "$FAKE_ANSWER"')
        self.executable('sleep', 'exit 0')
        self.env = {**os.environ, 'HOME': str(self.home),
                    'DESKMATE_DATA_DIR': str(self.data),
                    'PATH': str(self.executables) + ':/usr/bin:/bin',
                    'DESKMATE_DRY_RUN': '', 'FAKE_ANSWER': 'Ok, closing'}
        self.configure(['codex'], 'codex')

    def executable(self, name, body):
        path = self.executables / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)

    def configure(self, installed, default, language='en'):
        self.config = {'schema_version': 1, 'language': language,
                       'providers': {'installed': installed, 'default': default},
                       'reminders': {'morning': '09:00',
                                     'evening': '09:00',
                                     'days': ['mon', 'fri'], 'channels': ['mac', 'calendar']}}
        self.save_config()

    def save_config(self):
        (self.data / 'config.json').write_text(json.dumps(self.config))

    def cli(self, *args):
        python = str(self.executables / 'python3') if args[0] == 'window' else sys.executable
        return subprocess.run([python, '-B', str(ROOT / 'bin/deskmate'),
                               'reminders', *args], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def script(self, kind, **env):
        return subprocess.run(['/bin/zsh', str(ROOT / 'tools' / (kind + '_reminder.sh'))],
                              env={**self.env, **env}, text=True, capture_output=True, timeout=10)

    def rows(self):
        with (self.data / 'log.csv').open(newline='') as stream:
            return list(csv.DictReader(stream))

    def calendar(self):
        result = self.cli('ics')
        self.assertEqual(result.returncode, 0, result.stderr)
        raw = (self.data / 'deskmate-reminders.ics').read_bytes()
        self.assertTrue(all(len(line) <= 75 for line in raw.split(b'\r\n')))
        return raw.decode().replace('\r\n ', '')

    def test_single_provider_native_syntax_in_text_and_calendar(self):
        for provider, wanted, unwanted in [('claude', '/', '$'), ('codex', '$', '/')]:
            for language in ('en', 'it'):
                with self.subTest(provider=provider, language=language):
                    self.configure([provider], provider, language)
                    morning = self.cli('text', 'morning')
                    evening = self.cli('text', 'evening')
                    self.assertEqual(morning.returncode, 0, morning.stderr)
                    self.assertEqual(evening.returncode, 0, evening.stderr)
                    calendar = self.calendar()
                    for skill, text in [('whats-on-today', morning.stdout),
                                        ('study-later', morning.stdout),
                                        ('checkpoint', evening.stdout),
                                        ('call-it-a-day', evening.stdout),
                                        ('how-did-it-go', calendar)]:
                        self.assertIn(wanted + skill, text)
                        self.assertNotIn(unwanted + skill, text)
                        self.assertIn(wanted + skill, calendar)
                        self.assertNotIn(unwanted + skill, calendar)

    def test_both_forms_follow_default_even_when_installed_list_is_reversed(self):
        for installed, default, first, second in [
                (['claude', 'codex'], 'codex', '$', '/'),
                (['codex', 'claude'], 'claude', '/', '$')]:
            with self.subTest(default=default):
                self.configure(installed, default)
                outputs = [self.cli('text', 'morning').stdout,
                           self.cli('text', 'evening').stdout, self.calendar()]
                for skill, index in [('whats-on-today', 0), ('study-later', 0),
                                     ('checkpoint', 1), ('call-it-a-day', 1),
                                     ('how-did-it-go', 2)]:
                    text = outputs[index]
                    self.assertIn(first + skill, text)
                    self.assertIn(second + skill, text)
                    self.assertLess(text.index(first + skill), text.index(second + skill))

    def test_both_study_invocations_include_the_argument(self):
        for language, argument in [('en', '<topic>'), ('it', '<argomento>')]:
            self.configure(['claude', 'codex'], 'codex', language)
            for output in (self.cli('text', 'morning').stdout, self.calendar()):
                self.assertIn('/study-later ' + argument, output)
                self.assertIn('$study-later ' + argument, output)

    def test_language_fallback_topic_count_buttons_and_calendar_escaping(self):
        self.configure(['codex'], 'codex', 'it')
        (self.data / 'study-later.md').write_text('- [ ] uno\n- [x] due\n- [ ] tre\n')
        morning = self.cli('text', 'morning').stdout.splitlines()
        evening = self.cli('text', 'evening').stdout.splitlines()
        self.assertEqual(morning[0], 'Buongiorno, si riparte')
        self.assertEqual(morning[-1], 'Ok, si parte')
        self.assertEqual(evening[-2:], ['Tra 30 minuti', 'Ok, chiudo'])
        self.assertIn('2 argomenti', evening[1])
        self.assertIn('$whats-on-today', morning[1])
        calendar = self.calendar()
        self.assertIn('rilegge le consegne di ieri\\, controlla', calendar)
        self.assertIn('\\n2.', calendar)
        self.assertIn('RRULE:FREQ=WEEKLY;BYDAY=MO,FR', calendar)
        self.assertNotIn('2 argomenti', calendar)
        self.assertEqual(self.cli('ics').stdout.strip(), 'unchanged')
        self.config['language'] = 'xx'
        self.save_config()
        self.assertTrue(self.cli('text', 'morning').stdout.startswith("Good morning, let's go\n"))

    def test_provider_change_refreshes_calendar(self):
        original = self.calendar()
        self.configure(['claude'], 'claude')
        result = self.cli('ics')
        self.assertEqual(result.stdout.strip(), 'changed')
        self.assertNotEqual(self.calendar(), original)

    def test_legacy_configuration_keeps_claude_reminders(self):
        del self.config['providers']
        self.save_config()
        result = self.cli('text', 'morning')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('/whats-on-today', result.stdout)
        self.assertNotIn('$whats-on-today', result.stdout)

    def test_invalid_provider_configuration_fails_without_output_or_log(self):
        for selection in [None, {}, {'installed': [], 'default': 'codex'},
                          {'installed': ['codex'], 'default': 'claude'},
                          {'installed': ['unknown'], 'default': 'unknown'},
                          {'installed': ['codex', 'codex'], 'default': 'codex'},
                          {'installed': [{}], 'default': 'codex'}]:
            with self.subTest(selection=selection):
                self.config['providers'] = selection
                self.save_config()
                result = self.cli('text', 'morning')
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertIn('deskmate configure', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
        self.assertFalse((self.data / 'log.csv').exists())

    def test_desktop_responses_use_configured_default_without_session_identity(self):
        for provider, day in [('claude', '2026-11-16'), ('codex', '2026-11-20')]:
            self.clock.write_text(day + 'T09:10:00')
            self.configure(['claude', 'codex'], provider)
            for kind in ('morning', 'evening'):
                result = self.script(kind)
                self.assertEqual(result.returncode, 0, result.stderr)
        rows = self.rows()
        self.assertEqual([(r['event'], r['provider'], r['detail']) for r in rows],
                         [('morning-reminder', 'claude', 'Ok, closing'),
                          ('evening-reminder', 'claude', 'Ok, closing'),
                          ('morning-reminder', 'codex', 'Ok, closing'),
                          ('evening-reminder', 'codex', 'Ok, closing')])
        self.assertTrue(all(r['session'] == '' and r['cwd'] == '' for r in rows))

    def test_response_keeps_the_default_displayed_before_configuration_changes(self):
        self.configure(['claude', 'codex'], 'claude')
        self.executable('osascript', '\n'.join([
            "python3 - <<'PY'",
            'import json, os',
            'from pathlib import Path',
            'path = Path(os.environ["DESKMATE_DATA_DIR"]) / "config.json"',
            'config = json.loads(path.read_text())',
            'config["providers"]["default"] = "codex"',
            'path.write_text(json.dumps(config))',
            'PY',
            'printf "Ok, closing"']))
        for kind in ('morning', 'evening'):
            self.configure(['claude', 'codex'], 'claude')
            result = self.script(kind)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r['provider'] for r in self.rows()], ['claude', 'claude'])

    def test_malformed_activity_log_returns_a_concise_error_without_mutation(self):
        log = self.data / 'log.csv'
        header = ('date,time,weekday,event,detail,session,cwd,turns,input_tokens,'
                  'cache_tokens,output_tokens,schema_version,provider')
        original = header + '\n"unterminated\n'
        log.write_text(original)
        result = self.script('morning')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('unexpected end of data', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(log.read_text(), original)

    def test_evening_snooze_and_ignored_response_keep_logging(self):
        self.executable('osascript', 'if [ ! -e "$HOME/snoozed" ]; then\n'
                        '  touch "$HOME/snoozed"\n  printf "In 30 minutes"\nfi')
        result = self.script('evening')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([(r['detail'], r['provider']) for r in self.rows()],
                         [('In 30 minutes', 'codex'), ('ignored', 'codex')])

    def test_dry_run_prints_native_syntax_without_logging(self):
        for kind, skill in [('morning', 'whats-on-today'), ('evening', 'checkpoint')]:
            result = self.script(kind, DESKMATE_DRY_RUN='1')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('$' + skill, result.stdout)
        self.assertFalse((self.data / 'log.csv').exists())

    def test_launchagent_schedule_is_preserved(self):
        result = self.cli('plist', 'morning')
        self.assertEqual(result.returncode, 0, result.stderr)
        plist = plistlib.loads(result.stdout.encode())
        hour, minute = map(int, self.config['reminders']['morning'].split(':'))
        self.assertEqual(plist['StartCalendarInterval'],
                         [{'Weekday': 1, 'Hour': hour, 'Minute': minute},
                          {'Weekday': 5, 'Hour': hour, 'Minute': minute}])
        self.assertEqual(plist['ProgramArguments'], [str(ROOT / 'tools/morning_reminder.sh')])

    def test_login_trigger_is_morning_only(self):
        morning = plistlib.loads(self.cli('plist', 'morning').stdout.encode())
        evening = plistlib.loads(self.cli('plist', 'evening').stdout.encode())
        self.assertIs(morning.get('RunAtLoad'), True)
        self.assertNotIn('RunAtLoad', evening)

    def test_morning_window_respects_working_days_and_inclusive_limits(self):
        # Removing the working-day guard or shifting either boundary is a bug.
        for now, wanted in [('2026-11-16T08:54:59', 1),
                            ('2026-11-16T08:55:00', 0),
                            ('2026-11-16T12:00:00', 0),
                            ('2026-11-16T12:00:01', 1),
                            ('2026-11-17T09:10:00', 1),
                            ('2026-11-21T09:10:00', 1)]:
            with self.subTest(now=now):
                self.clock.write_text(now)
                self.assertEqual(self.cli('window', 'morning').returncode, wanted)

    def test_login_outside_window_does_not_consume_the_working_day(self):
        self.executable('osascript', 'echo shown >> "$HOME/displays"; printf accepted')
        for now in ['2026-11-16T08:54:59', '2026-11-16T12:00:01',
                    '2026-11-17T09:10:00', '2026-11-21T09:10:00']:
            self.clock.write_text(now)
            self.assertEqual(self.script('morning').returncode, 0)
        self.assertFalse((self.home / 'displays').exists())
        self.clock.write_text('2026-11-16T09:31:00')
        self.assertEqual(self.script('morning').returncode, 0)
        self.assertEqual((self.home / 'displays').read_text().splitlines(), ['shown'])

    def test_dry_run_does_not_claim_and_next_working_day_displays_again(self):
        self.executable('osascript', 'echo shown >> "$HOME/displays"; printf accepted')
        self.assertEqual(self.script('morning', DESKMATE_DRY_RUN='1').returncode, 0)
        for now in ['2026-11-16T08:58:00', '2026-11-16T09:00:00',
                    '2026-11-20T09:07:00', '2026-11-20T09:11:00']:
            self.clock.write_text(now)
            self.assertEqual(self.script('morning').returncode, 0)
        self.assertEqual((self.home / 'displays').read_text().splitlines(), ['shown', 'shown'])

    def test_concurrent_login_and_schedule_do_not_duplicate_an_unanswered_alert(self):
        self.executable('osascript', 'echo shown >> "$HOME/displays"\n'
                        'while [ ! -e "$HOME/answer" ]; do /bin/sleep 0.02; done\n'
                        'printf accepted')
        command = ['/bin/zsh', str(ROOT / 'tools/morning_reminder.sh')]
        processes = [subprocess.Popen(command, env=self.env, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True) for _ in range(6)]
        try:
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if ((self.home / 'displays').exists()
                        and sum(process.poll() is not None for process in processes) >= 5):
                    break
                time.sleep(0.02)
            self.assertEqual(sum(process.poll() is not None for process in processes), 5,
                             'duplicate callers must finish while the alert is unanswered')
            self.assertEqual((self.home / 'displays').read_text().splitlines(), ['shown'])
            self.assertFalse((self.data / 'log.csv').exists(), 'claim must precede response logging')
            # A later scheduled trigger still cannot duplicate the open alert.
            self.assertEqual(self.script('morning').returncode, 0)
            self.assertEqual((self.home / 'displays').read_text().splitlines(), ['shown'])
        finally:
            (self.home / 'answer').touch()
            for process in processes:
                process.communicate(timeout=8)
        self.assertEqual([process.returncode for process in processes], [0] * 6)
        self.assertEqual([row['detail'] for row in self.rows()], ['accepted'])


if __name__ == '__main__':
    unittest.main()
