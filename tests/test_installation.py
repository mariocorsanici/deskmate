"""Setup/removal acceptance through the public command, in disposable homes."""
import csv
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'bin/deskmate'
LEGACY_FIELDS = 'date,time,weekday,event,detail,session,cwd,turns,input_tokens,cache_tokens,output_tokens'


class InstallationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.binaries = self.home / 'fake-bin'
        self.binaries.mkdir()
        # PATH cannot discover the owner's installed Providers or launchctl.
        (self.binaries / 'python3').symlink_to(sys.executable)
        self.executable('osascript', 'exit 99')
        self.env = {**os.environ, 'HOME': str(self.home),
                    'CODEX_HOME': str(self.home / '.codex'),
                    'DESKMATE_DATA_DIR': str(self.home / 'data'),
                    'SHELL': '/bin/zsh', 'PATH': str(self.binaries),
                    'PYTHONDONTWRITEBYTECODE': '1'}
        self.config = self.home / 'data/config.json'
        self.config.parent.mkdir()
        self.config.write_text(json.dumps({'name': 'Test', 'language': 'it',
                                          'reminders': {'channels': []}, 'custom': [42]}))

    def executable(self, name, body):
        path = self.binaries / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)
        return path

    def providers(self, *names, hooks=True):
        for name in names:
            body = 'echo "Claude Code 2.1.0"' if name == 'claude' else (
                'case "$1" in --version) echo "codex-cli 0.166.0";; '
                'features) echo "hooks experimental ' + ('true' if hooks else 'false') + '";; '
                '*) exit 90;; esac')
            self.executable(name, body)

    def cli(self, *args, input_text=None):
        return subprocess.run([sys.executable, '-B', str(COMMAND), *map(str, args)],
                              env=self.env, cwd=self.home, input=input_text,
                              capture_output=True, text=True, timeout=25)

    def setup(self, *args):
        return self.cli('setup', '--non-interactive', *args)

    def succeeds(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def legacy_card(self, name='Demo Project'):
        project = self.home / name
        project.mkdir()
        key = re.sub(r'[^a-zA-Z0-9]', '-', str(project))
        legacy = self.home / '.claude/projects' / key / 'memory/project-card.md'
        legacy.parent.mkdir(parents=True)
        legacy.write_text(f'# Demo\n\n## Status\nCheckpoint 2026-11-09 12:00, '
                          f'session `old-session`, folder `{project}`.\n'
                          '- **State:** active\n\n## Checks\n- ready: `printf ready`\n')
        return project, legacy

    def test_each_provider_and_dual_setup_links_one_source_and_verifies_logging(self):
        for names, default in [(('claude',), 'claude'), (('codex',), 'codex'),
                               (('claude', 'codex'), 'codex')]:
            with self.subTest(names=names):
                self.providers(*names)
                result = self.setup('--default-provider', default)
                self.succeeds(result)
                self.assertEqual(json.loads(self.config.read_text())['providers'],
                                 {'installed': list(names), 'default': default})
                self.assertEqual(json.loads(self.config.read_text())['custom'], [42])
                for provider in names:
                    location = '.claude' if provider == 'claude' else '.agents'
                    for skill in (ROOT / 'skills').iterdir():
                        if not (skill / 'SKILL.md').is_file():
                            continue
                        link = self.home / location / 'skills' / skill.name
                        self.assertTrue(link.is_symlink(), link)
                        self.assertEqual(link.resolve(), skill)
                    self.assertIn(f'{provider}: logging verified', result.stdout)
                self.assertIn('native', result.stdout.lower())
                self.assertFalse((self.home / 'data/log.csv').exists())
                self.succeeds(self.cli('remove', '--non-interactive'))
                for name in names:
                    (self.binaries / name).unlink()

    def test_default_and_requested_provider_are_explicit_before_mutation(self):
        self.providers('claude', 'codex')
        before = self.config.read_bytes()
        result = self.setup()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('--default-provider', result.stderr)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.home / '.claude').exists())
        self.succeeds(self.setup('--provider', 'codex'))
        self.assertEqual(json.loads(self.config.read_text())['providers'],
                         {'installed': ['codex'], 'default': 'codex'})
        self.assertFalse((self.home / '.claude/skills').exists())

    def test_override_removes_previously_installed_provider_without_removing_personal_hooks(self):
        self.providers('claude', 'codex')
        self.succeeds(self.setup('--default-provider', 'claude'))
        self.succeeds(self.setup('--provider', 'codex'))
        self.assertFalse((self.home / '.claude/skills/checkpoint').is_symlink())
        settings = json.loads((self.home / '.claude/settings.json').read_text())
        self.assertFalse(settings.get('hooks'))
        self.assertTrue((self.home / '.agents/skills/checkpoint').is_symlink())

    def test_config_and_log_modes_and_original_config_format_survive_noop_setup(self):
        self.providers('claude')
        self.succeeds(self.setup())
        config = json.loads(self.config.read_text())
        self.config.write_text(json.dumps(config, separators=(',', ':')))
        self.config.chmod(0o640)
        original = self.config.read_bytes()
        self.succeeds(self.setup())
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o640)

    def test_installed_command_records_a_provider_owned_native_event(self):
        self.providers('codex')
        self.succeeds(self.setup())
        result = subprocess.run([str(self.home / '.local/bin/deskmate'), 'hook-event',
                                 '--provider', 'codex'], env=self.env, capture_output=True,
                                text=True, input=json.dumps({'hook_event_name': 'UserPromptSubmit',
                                'prompt': '$checkpoint example', 'session_id': 'native-123',
                                'cwd': str(self.home)}))
        self.succeeds(result)
        with (self.home / 'data/log.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([(r['provider'], r['session'], r['event'], r['detail']) for r in rows],
                         [('codex', 'native-123', 'checkpoint', 'example')])

    def test_existing_card_symlink_from_another_data_root_is_preserved_on_failure(self):
        self.providers('claude')
        _, legacy = self.legacy_card()
        foreign = self.home / 'different-data/project-card.md'
        foreign.parent.mkdir()
        foreign.write_text('keep foreign card')
        legacy.unlink()
        legacy.symlink_to(foreign)
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(legacy.resolve(), foreign)
        self.assertEqual(foreign.read_text(), 'keep foreign card')
        self.assertFalse((self.home / 'data/backups').exists())

    def test_index_metadata_can_identify_a_card_without_reading_transcripts(self):
        self.providers('claude')
        project, legacy = self.legacy_card()
        legacy.write_text('# Legacy without a folder\n')
        index = legacy.parent.parent / 'sessions-index.json'
        index.write_text(json.dumps({'version': 1, 'entries': [], 'originalPath': str(project)}))
        (index.parent / 'private-session.jsonl').write_bytes(b'\xff secret transcript not read')
        self.succeeds(self.setup())
        self.assertTrue(legacy.is_symlink())

    def test_missing_previously_recorded_project_is_not_silently_dropped(self):
        self.providers('claude')
        project, legacy = self.legacy_card()
        project.rmdir()
        before = legacy.read_bytes()
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--project', result.stderr)
        self.assertEqual(legacy.read_bytes(), before)

    def test_no_compatible_provider_and_explicit_unavailable_override_leave_data(self):
        before = self.config.read_bytes()
        self.assertNotEqual(self.setup().returncode, 0)
        self.providers('claude')
        self.assertNotEqual(self.setup('--provider', 'codex').returncode, 0)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.home / 'data/backups').exists())

    def test_disabled_codex_hooks_are_excluded_but_explicit_request_fails(self):
        self.providers('claude', 'codex', hooks=False)
        result = self.setup()
        self.succeeds(result)
        self.assertEqual(json.loads(self.config.read_text())['providers']['installed'], ['claude'])
        self.assertIn('disabled', result.stdout)
        self.assertNotEqual(self.setup('--provider', 'codex').returncode, 0)

    def test_codex_capability_staging_retains_custom_home_configuration(self):
        custom = self.home / 'alternate codex'
        custom.mkdir()
        self.env['CODEX_HOME'] = str(custom)
        original = b'[features]\nhooks = true\n# preserve my configuration\n'
        (custom / 'config.toml').write_bytes(original)
        self.executable('codex', 'case "$1" in --version) echo "codex-cli 0.166.0";; '
                        'features) if [ -f "$CODEX_HOME/config.toml" ]; then '
                        'echo "hooks experimental true"; else echo "hooks experimental false"; fi;; '
                        '*) exit 90;; esac')
        result = self.setup('--provider', 'codex')
        self.succeeds(result)
        self.assertTrue((custom / 'hooks.json').is_file())
        self.assertEqual((custom / 'config.toml').read_bytes(), original)

    def test_noop_setup_activation_failure_has_a_recoverable_journal(self):
        self.providers('claude')
        self.config.write_text(json.dumps({'reminders': {'channels': ['mac']}}))
        self.fake_launchctl()
        self.succeeds(self.setup())
        journals = list((self.home / 'data/backups/install').glob('*/transaction.json'))
        # All installed bytes are unchanged, but inactive services need activation.
        self.fake_launchctl(failing=True)
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        new = set((self.home / 'data/backups/install').glob('*/transaction.json')) - set(journals)
        self.assertEqual(len(new), 1)
        value = json.loads(next(iter(new)).read_text())
        self.assertEqual(value['status'], 'rolled-back')
        self.assertEqual(len(value['metadata']['reminders']), 2)

    def test_repeated_setup_preserves_unrelated_hooks_and_shell_configuration(self):
        self.providers('claude', 'codex')
        settings = self.home / '.claude/settings.json'
        settings.parent.mkdir()
        foreign = {'type': 'command', 'command': 'echo personal'}
        settings.write_text(json.dumps({'model': 'keep', 'hooks': {
            'UserPromptSubmit': [{'matcher': '*', 'hooks': [foreign]}]}}))
        (self.home / '.zshrc').write_text('# personal\nexport PERSONAL=keep\n')
        self.succeeds(self.setup('--default-provider', 'codex'))
        before = {p: p.read_bytes() for p in [self.config, settings,
                  self.home / '.codex/hooks.json', self.home / '.zshrc']}
        self.succeeds(self.setup('--default-provider', 'codex'))
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw, path)
        value = json.loads(settings.read_text())
        self.assertEqual(value['model'], 'keep')
        self.assertEqual(value['hooks']['UserPromptSubmit'][0]['hooks'], [foreign])
        result = subprocess.run(['/bin/zsh', '-d', '-i', '-c', 'command -v deskmate'],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), str(self.home / '.local/bin/deskmate'))
        self.succeeds(self.cli('remove', '--non-interactive'))
        self.assertEqual(json.loads(settings.read_text()), {'model': 'keep', 'hooks': {
            'UserPromptSubmit': [{'matcher': '*', 'hooks': [foreign]}]}})
        self.assertEqual((self.home / '.zshrc').read_text(), '# personal\nexport PERSONAL=keep\n')

    def test_config_cards_and_log_migrate_with_exact_backups_and_repeat_safely(self):
        self.providers('claude')
        project, legacy = self.legacy_card()
        original = {self.config: self.config.read_bytes(), legacy: legacy.read_bytes()}
        log = self.home / 'data/log.csv'
        log.write_text(LEGACY_FIELDS + ',extra\n2026-11-01,12:00,sun,checkpoint,,old,'
                       + str(project) + ',1,2,3,4,keep\n')
        original[log] = log.read_bytes()
        result = self.setup()
        self.succeeds(result)
        self.assertTrue(legacy.is_symlink())
        shared = legacy.resolve()
        self.assertTrue(shared.is_file())
        self.assertIn('"provider":"claude"', shared.read_text())
        self.assertIn('"session_id":"old-session"', shared.read_text())
        self.assertTrue(shared.read_bytes().endswith(original[legacy]))
        with log.open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([(r['provider'], r['schema_version'], r['extra']) for r in rows],
                         [('claude', '1', 'keep')])
        backups = [p.read_bytes() for p in (self.home / 'data/backups').rglob('*') if p.is_file()]
        for path, raw in original.items():
            self.assertIn(raw, backups, path)
            self.assertIn(str(path), result.stdout)
        before = shared.read_bytes()
        self.succeeds(self.setup())
        self.assertEqual(shared.read_bytes(), before)

    def test_future_schema_anywhere_is_rejected_before_any_migration(self):
        self.providers('claude')
        _, legacy = self.legacy_card()
        original = self.config.read_bytes(), legacy.read_bytes()
        future = self.home / 'data/projects/future/project-card.md'
        future.parent.mkdir(parents=True)
        future.write_text('---\ndeskmate: {"schema_version":99,"revision":1,'
                          '"provider":null,"session_id":null}\n---\nFuture\n')
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('schema', result.stderr)
        self.assertEqual((self.config.read_bytes(), legacy.read_bytes()), original)
        self.assertFalse((self.home / 'data/backups').exists())
        self.assertFalse((self.home / '.local').exists())

    def test_unresolvable_card_requires_explicit_project_without_guessing(self):
        self.providers('claude')
        project, legacy = self.legacy_card()
        legacy.write_text('# Old card without a folder\n')
        before = self.config.read_bytes()
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--project', result.stderr)
        self.assertEqual(self.config.read_bytes(), before)
        self.succeeds(self.setup('--project', project))
        self.assertTrue(legacy.is_symlink())

    def test_foreign_skill_collision_aborts_without_partial_installation(self):
        self.providers('claude', 'codex')
        collision = self.home / '.agents/skills/checkpoint'
        collision.mkdir(parents=True)
        (collision / 'SKILL.md').write_text('personal skill')
        before = self.config.read_bytes()
        result = self.setup('--default-provider', 'claude')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.home / '.claude/settings.json').exists())
        self.assertFalse((self.home / '.claude/skills').exists())
        self.assertEqual((collision / 'SKILL.md').read_text(), 'personal skill')

    def test_remove_keeps_all_personal_data_and_foreign_links_without_providers(self):
        self.providers('codex')
        self.succeeds(self.setup())
        personal = self.home / 'data/handoff.md'
        personal.write_text('keep my history')
        foreign = self.home / '.agents/skills/checkpoint'
        foreign.unlink()
        target = self.home / 'my-checkpoint'
        target.mkdir()
        foreign.symlink_to(target)
        (self.binaries / 'codex').unlink()
        before = self.config.read_bytes()
        self.succeeds(self.cli('remove', '--non-interactive'))
        self.assertEqual(personal.read_text(), 'keep my history')
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(foreign.resolve(), target)
        self.assertFalse((self.home / '.local/bin/deskmate').is_symlink())
        self.succeeds(self.cli('remove', '--non-interactive'))

    def test_unattended_purge_requires_the_explicit_option(self):
        self.providers('claude')
        _, legacy = self.legacy_card()
        self.succeeds(self.setup())
        self.succeeds(self.cli('remove', '--non-interactive', input_text='DELETE\n'))
        self.assertTrue(self.config.exists())
        self.succeeds(self.cli('remove', '--non-interactive', '--purge-data'))
        self.assertFalse(self.config.parent.exists())
        self.assertFalse(legacy.is_symlink())

    def test_purge_refuses_a_data_root_containing_the_repository(self):
        # The entire reproduction is disposable, including the copied repository.
        parent = self.home / 'workspace'
        repo = parent / 'deskmate'
        shutil.copytree(ROOT / 'tools', repo / 'tools')
        (repo / 'skills').mkdir()
        (repo / 'bin').mkdir()
        shutil.copy2(COMMAND, repo / 'bin/deskmate')
        marker = parent / 'unrelated.txt'
        marker.write_text('keep workspace')
        result = subprocess.run([sys.executable, '-B', str(repo / 'bin/deskmate'),
                                 'remove', '--non-interactive', '--purge-data'],
                                env={**self.env, 'DESKMATE_DATA_DIR': str(parent)},
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unsafe data purge root', result.stderr)
        self.assertEqual(marker.read_text(), 'keep workspace')

    def test_install_wrapper_uses_the_same_setup_and_removal(self):
        self.providers('claude')
        result = subprocess.run(['/bin/zsh', str(ROOT / 'install.sh'), '--non-interactive'],
                                env=self.env, capture_output=True, text=True, timeout=25)
        self.succeeds(result)
        self.assertTrue((self.home / '.local/bin/deskmate').is_symlink())
        result = subprocess.run(['/bin/zsh', str(ROOT / 'install.sh'), '--remove', '--non-interactive'],
                                env=self.env, capture_output=True, text=True, timeout=25)
        self.succeeds(result)
        self.assertTrue(self.config.exists())

    def interactive(self, command, answers, *flags):
        master, slave = pty.openpty()
        process = subprocess.Popen([sys.executable, '-B', str(COMMAND), command, *flags],
                                   stdin=slave, stdout=slave, stderr=slave, env=self.env)
        os.close(slave)
        output = b''
        try:
            for prompt, answer in answers:
                deadline = time.monotonic() + 15
                while prompt.encode() not in output:
                    if time.monotonic() > deadline or process.poll() is not None:
                        self.fail('Missing prompt ' + prompt + ': ' + output.decode())
                    if select.select([master], [], [], 0.1)[0]:
                        try:
                            output += os.read(master, 65536)
                        except OSError:
                            self.fail(output.decode())
                os.write(master, answer.encode() + b'\n')
            deadline = time.monotonic() + 20
            while process.poll() is None and time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        output += os.read(master, 65536)
                    except OSError:
                        break
            process.wait(timeout=2)
            return process.returncode
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)

    def test_interactive_default_and_purge_default_no_then_exact_delete(self):
        self.providers('claude', 'codex')
        self.assertEqual(self.interactive('setup', [('Default provider:', 'codex')]), 0)
        self.assertEqual(self.interactive('remove', [('Purge personal data?', '')]), 0)
        self.assertTrue(self.config.exists())
        self.assertEqual(self.interactive('remove', [('Purge personal data?', 'y'),
                                                    ('Type DELETE', 'delete')]), 2)
        self.assertTrue(self.config.exists())
        self.assertEqual(self.interactive('remove', [('Type DELETE', 'DELETE ')] , '--purge-data'), 2)
        self.assertTrue(self.config.exists())
        self.assertEqual(self.interactive('remove', [('Type DELETE', 'DELETE')], '--purge-data'), 0)
        self.assertFalse(self.config.parent.exists())

    def test_future_config_and_log_are_rejected_without_hooks_or_backups(self):
        self.providers('claude')
        for config, log in [({'schema_version': 9}, None),
                            ({}, LEGACY_FIELDS + ',schema_version,provider\n'
                             '2026-11-09,12:00,mon,checkpoint,,,,,,,,9,claude\n')]:
            with self.subTest(config=config):
                self.config.write_text(json.dumps(config))
                if log:
                    (self.config.parent / 'log.csv').write_text(log)
                before = self.config.read_bytes()
                result = self.setup()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('schema', result.stderr)
                self.assertEqual(self.config.read_bytes(), before)
                self.assertFalse((self.home / 'data/backups').exists())
                self.assertFalse((self.home / '.claude').exists())

    def test_tilde_data_root_validates_actual_schema_and_preserves_actual_preferences(self):
        self.providers('claude')
        self.fake_launchctl()
        self.env['DESKMATE_DATA_DIR'] = '~/data'
        self.config.write_text(json.dumps({'schema_version': 99, 'name': 'Future'}))
        original = self.config.read_bytes()
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('schema', result.stderr)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.config.parent / 'backups').exists())
        self.config.write_text(json.dumps({'name': 'Actual preferences', 'reminders': {'channels': []}}))
        self.succeeds(self.setup())
        self.assertEqual(json.loads(self.config.read_text())['name'], 'Actual preferences')

    def test_setup_refuses_config_modified_between_parse_and_publication_snapshot(self):
        self.providers('claude')
        # Emulate an independent preference writer at the read boundary, without
        # replacing the installer or its actual file publication behavior.
        script = f'''import json, sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'tools')!r})
import installation
original_read = installation.providers.read_config
reads = 0
def concurrent_read():
    global reads
    config = original_read()
    reads += 1
    if reads == 2:
        changed = dict(config, name='Concurrent edit')
        Path({str(self.config)!r}).write_text(json.dumps(changed))
    return config
installation.providers.read_config = concurrent_read
sys.argv = ['installation.py', 'setup', '--non-interactive']
raise SystemExit(installation.main())
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], env=self.env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.config.read_text())['name'], 'Concurrent edit')

    def test_failed_service_restoration_keeps_pending_journal_for_retry(self):
        self.providers('claude')
        self.config.write_text(json.dumps({'reminders': {'channels': ['mac']}}))
        executable = self.executable('launchctl', '')
        executable.write_text('#!' + sys.executable + '\n' + '''import json, os, pathlib, sys
h = pathlib.Path(os.environ['HOME'])
p = h / 'active-services.json'
active = json.loads(p.read_text()) if p.exists() else []
verb = sys.argv[1]
label = sys.argv[-1].rsplit('/', 1)[-1].replace('.plist', '')
if verb == 'print':
    sys.exit(0 if label in active else 1)
if verb == 'bootout':
    if label in active:
        sys.exit(18)
elif verb == 'bootstrap':
    if label == 'com.deskmate.evening':
        sys.exit(17)
    active.append(label)
p.write_text(json.dumps(active))
''')
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        journals = list((self.home / 'data/backups/install').glob('*/transaction.json'))
        self.assertEqual(len(journals), 1)
        self.assertEqual(json.loads(journals[0].read_text())['status'], 'pending')
        self.assertIn('recovery needs attention', result.stderr)

    def fake_launchctl(self, failing=False, pause=False):
        self.executable('launchctl',
                        'case "$1" in print) exit 1;; bootout) exit 0;; bootstrap) '
                        + (f'echo ready > "{self.home}/launch-ready"; /bin/sleep 20; exit 17'
                           if pause else 'echo denied >&2; exit 17' if failing else 'exit 0')
                        + ';; *) exit 91;; esac')

    def test_reminders_include_selected_data_root_and_removal_preserves_foreign_agent(self):
        self.providers('codex')
        self.fake_launchctl()
        self.config.write_text(json.dumps({'reminders': {'channels': ['mac', 'calendar']}}))
        self.succeeds(self.setup())
        import plistlib
        agent = self.home / 'Library/LaunchAgents/com.deskmate.morning.plist'
        value = plistlib.loads(agent.read_bytes())
        self.assertEqual(value['EnvironmentVariables']['DESKMATE_DATA_DIR'], str(self.home / 'data'))
        calendar = self.home / 'data/deskmate-reminders.ics'
        self.assertIn('$whats-on-today', calendar.read_text())
        agent.write_bytes(plistlib.dumps({'Label': 'com.deskmate.morning',
                                         'ProgramArguments': ['/personal/reminder']}))
        self.succeeds(self.cli('remove', '--non-interactive'))
        self.assertTrue(agent.exists())
        self.assertTrue(calendar.exists())

    def test_launch_failure_rolls_back_config_cards_logs_hooks_and_links(self):
        self.providers('claude')
        self.fake_launchctl(failing=True)
        self.config.write_text(json.dumps({'reminders': {'channels': ['mac']}}))
        _, legacy = self.legacy_card()
        before = self.config.read_bytes(), legacy.read_bytes()
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('launchctl', result.stderr)
        self.assertEqual((self.config.read_bytes(), legacy.read_bytes()), before)
        self.assertFalse(legacy.is_symlink())
        self.assertFalse((self.home / '.claude/settings.json').exists())
        self.assertFalse((self.home / '.local/bin/deskmate').is_symlink())
        self.assertFalse(list((self.home / 'data/projects').glob('*/project-card.md')))

    def test_interrupted_install_is_recovered_before_a_new_install(self):
        self.providers('claude')
        self.fake_launchctl(pause=True)
        self.config.write_text(json.dumps({'reminders': {'channels': ['mac']}}))
        self.interrupt_setup()
        self.fake_launchctl()
        result = self.setup()
        self.succeeds(result)
        self.assertIn('Recovered interrupted', result.stdout)
        self.assertEqual(json.loads(self.config.read_text())['providers']['installed'], ['claude'])

    def interrupt_setup(self):
        process = subprocess.Popen([sys.executable, '-B', str(COMMAND), 'setup', '--non-interactive'],
                                   env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        try:
            deadline = time.monotonic() + 15
            while not (self.home / 'launch-ready').exists():
                if time.monotonic() > deadline or process.poll() is not None:
                    self.fail('setup did not reach reminder activation')
                time.sleep(0.05)
            import signal
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()

    def test_interrupted_activation_recovers_prior_service_state_even_when_followed_by_remove(self):
        self.providers('claude')
        self.config.write_text(json.dumps({'reminders': {'channels': ['mac']}}))
        script = self.executable('launchctl', '')
        script.write_text('#!' + sys.executable + '\n' + '''import json, os, pathlib, sys, time
h = pathlib.Path(os.environ['HOME'])
p = h / 'active-services.json'
active = json.loads(p.read_text()) if p.exists() else []
verb = sys.argv[1]
label = sys.argv[-1].rsplit('/', 1)[-1].replace('.plist', '')
if verb == 'print':
    sys.exit(0 if label in active else 1)
if verb == 'bootout':
    active = [x for x in active if x != label]
elif verb == 'bootstrap':
    active.append(label)
p.write_text(json.dumps(active))
if verb == 'bootstrap' and (h / 'pause-launch').exists():
    (h / 'launch-ready').write_text('ready')
    time.sleep(20)
''')
        pause = self.home / 'pause-launch'
        pause.touch()
        self.interrupt_setup()
        self.assertEqual(json.loads((self.home / 'active-services.json').read_text()), ['com.deskmate.morning'])
        pause.unlink()
        self.succeeds(self.cli('remove', '--non-interactive'))
        self.assertEqual(json.loads((self.home / 'active-services.json').read_text()), [])

    def test_recovery_refuses_to_overwrite_a_concurrent_config_edit(self):
        self.providers('claude')
        self.fake_launchctl(pause=True)
        self.config.write_text(json.dumps({'reminders': {'channels': ['mac']}}))
        self.interrupt_setup()
        config = json.loads(self.config.read_text())
        config['name'] = 'Concurrent edit'
        self.config.write_text(json.dumps(config))
        before = self.config.read_bytes()
        self.fake_launchctl()
        result = self.setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Cannot recover changed file', result.stderr)
        self.assertEqual(self.config.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
