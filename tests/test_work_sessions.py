"""Routing acceptance through the public command, with no native model calls."""
import json
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkSessionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.project = self.home / 'Demo Project'
        self.project.mkdir()
        self.data = self.home / 'data'
        self.binaries = self.home / 'bin'
        self.binaries.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home),
                    'CODEX_HOME': str(self.home / '.codex'),
                    'DESKMATE_DATA_DIR': str(self.data), 'PATH': str(self.binaries),
                    'PYTHONDONTWRITEBYTECODE': '1'}
        self.env.pop('DESKMATE_LAUNCH_ID', None)
        self.env.pop('DESKMATE_DRY_RUN', None)
        for provider in ('claude', 'codex'):
            self.executable(provider, "import sys\nprint('" + provider + " 1.0.0')\n")
        self.executable('osascript', 'import sys\nsys.exit(0)\n')
        self.executable('ps', 'import sys\nsys.exit(0)\n')
        self.configure()

    def executable(self, name, text):
        path = self.binaries / name
        path.write_text('#!' + sys.executable + '\n' + text)
        path.chmod(0o755)
        return path

    def configure(self, default='codex', installed=None):
        self.data.mkdir(exist_ok=True)
        (self.data / 'config.json').write_text(json.dumps({
            'schema_version': 1, 'providers': {
                'installed': installed or ['claude', 'codex'], 'default': default}}))

    def cli(self, *args, env=None, payload=None, human=False):
        argv = [sys.executable, str(ROOT / 'bin/deskmate')]
        if not human:
            argv.append('--json')
        result = subprocess.run([*argv, *map(str, args)], env=env or self.env,
                                input=None if payload is None else json.dumps(payload),
                                capture_output=True, text=True, timeout=15)
        self.assertNotIn('Traceback', result.stderr)
        if human:
            return result.returncode, result.stdout
        envelope = json.loads(result.stdout)
        self.assertNotIn('Traceback', envelope['stderr'])
        return result.returncode, envelope

    def command(self, *args, code=0, env=None):
        rc, envelope = self.cli(*args, env=env)
        self.assertEqual(rc, code, envelope)
        return json.loads(envelope['stdout'])

    def route(self, *args, code=0, env=None):
        return self.command('work-session', '--folder', self.project, *args, code=code, env=env)

    def card(self, provider='claude', session='native-123', revision=0):
        source = self.home / 'candidate.md'
        source.write_text('---\nname: keep-me\n---\n# Demo\n\n## Status\nKeep this status.\n\n## Checks\n')
        self.command('card', 'write', self.project, '--expected-revision', revision,
                     '--provider', provider, '--session-id', session, '--from', source)
        return Path(self.command('card', 'locate', self.project)['path'])

    def native(self, provider, session='native-123', folder=None):
        folder = str(folder or self.project)
        if provider == 'claude':
            directory = self.home / '.claude/projects/demo'
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'sessions-index.json').write_text(json.dumps({'entries': [{
                'sessionId': session, 'projectPath': folder,
                'created': '2026-11-04T10:00:00Z', 'modified': '2026-11-04T10:00:00Z'}]}))
            # Must not be read as conversation data for routing.
            (directory / (session + '.jsonl')).write_text('NOT A TRANSCRIPT\n')
        else:
            directory = self.home / '.codex/sessions'
            directory.mkdir(parents=True, exist_ok=True)
            (directory / ('rollout-' + session + '.jsonl')).write_text(json.dumps({
                'type': 'session_meta', 'timestamp': '2026-11-04T10:00:00Z',
                'payload': {'id': session, 'cwd': folder}}) + '\nPRIVATE CONTENT\n')

    def tree(self):
        return {str(p.relative_to(self.data)): p.read_bytes()
                for p in self.data.rglob('*') if p.is_file()}

    def card_path(self):
        return Path(self.command('card', 'locate', self.project)['path'])

    def journal(self):
        return self.card_path().with_name('work-sessions.json')

    def hook(self, launch_id, provider='codex', session='new-native-456',
             event='SessionStart', folder=None, code=0):
        environment = {**self.env, 'DESKMATE_LAUNCH_ID': launch_id}
        return self.hook_payload(environment, provider, session, event, folder, code)

    def hook_payload(self, environment, provider, session, event, folder, code):
        rc, envelope = self.cli('hook-event', '--provider', provider, env=environment,
                               payload={'hook_event_name': event, 'session_id': session,
                                        'cwd': str(folder or self.project), 'prompt': 'harmless turn'})
        self.assertEqual(rc, code, envelope)
        if code == 0:
            self.assertEqual(json.loads(envelope['stdout']), {})
        return envelope

    def simulated_native(self, provider, *, fail_after=False, native_id=None):
        """Execute only a fake native CLI; its hook may beat terminal submission."""
        card = str(self.card_path())
        hook_command = [sys.executable, str(ROOT / 'bin/deskmate'), 'hook-event', '--provider', provider]
        body = ("import json,os,subprocess,sys\nfrom pathlib import Path\n"
                "if '--version' in sys.argv:\n    print('" + provider + " 1.0.0'); sys.exit(0)\n"
                "token=os.environ.get('DESKMATE_LAUNCH_ID')\n"
                "if not token: sys.exit('Missing launch correlation')\n"
                "card=Path(" + repr(card) + ")\n"
                "before=card.read_bytes() if card.exists() else None\n"
                "payload={'hook_event_name':'SessionStart','session_id':" + repr(native_id or 'native-' + provider) + ",'cwd':os.getcwd()}\n"
                "result=subprocess.run(" + repr(hook_command) + ",input=json.dumps(payload),capture_output=True,text=True)\n"
                "assert result.returncode == 0, result.stderr\n"
                "assert (card.read_bytes() if card.exists() else None) == before, 'Premature ownership commit'\n"
                "Path(os.environ['HOME'],'fake-native.json').write_text(json.dumps({'token':token,'argv':sys.argv[1:],"
                "'data':os.environ.get('DESKMATE_DATA_DIR'),'codex_home':os.environ.get('CODEX_HOME')}))\n")
        self.executable(provider, body)
        self.executable('osascript',
                        "import subprocess,sys\n"
                        "result=subprocess.run(['/bin/zsh','-c',sys.argv[2]],capture_output=True,text=True)\n"
                        "sys.stderr.write(result.stderr)\n"
                        "sys.exit(" + ('7' if fail_after else 'result.returncode') + ")\n")

    def test_recorded_provider_overrides_default(self):
        for provider, default in (('claude', 'codex'), ('codex', 'claude')):
            with self.subTest(provider=provider):
                self.configure(default)
                self.card(provider, revision=0 if provider == 'claude' else 1)
                self.native(provider)
                before = self.tree()
                result = self.route('--dry-run')
                self.assertEqual((result['mode'], result['provider'], result['session_id']),
                                 ('resume', provider, 'native-123'))
                self.assertEqual(self.tree(), before)

    def test_unowned_project_uses_default(self):
        for provider in ('claude', 'codex'):
            self.configure(provider)
            before = self.tree()
            result = self.route('--dry-run')
            self.assertEqual((result['mode'], result['provider']), ('new', provider))
            self.assertIsNone(result['session_id'])
            self.assertEqual(self.tree(), before)

    def test_missing_session_requires_explicit_new(self):
        card = self.card()
        before = card.read_bytes()
        result = self.route('--dry-run', code=4)
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(result['reason'], 'session_unavailable')
        self.assertTrue(result['choices'])
        result = self.route('--new', '--provider', 'codex', '--dry-run')
        self.assertEqual((result['mode'], result['provider']), ('new', 'codex'))
        self.assertEqual(card.read_bytes(), before)

    def test_indexless_claude_resume_uses_native_lifecycle_identity_without_reading_messages(self):
        self.card('claude')
        native = self.home / '.claude/projects/demo/native-123.jsonl'
        native.parent.mkdir(parents=True)
        native.write_bytes(b'\xff PRIVATE CONVERSATION MUST NOT BE READ\n')
        self.hook_payload(self.env, 'claude', 'native-123', 'SessionStart', None, 0)
        before = self.tree()
        result = self.route('--dry-run')
        self.assertEqual((result['mode'], result['provider'], result['session_id']),
                         ('resume', 'claude', 'native-123'))
        self.assertEqual(result['cwd'], str(self.project.resolve()))
        self.assertEqual(self.tree(), before)

    def test_indexless_claude_requires_unique_matching_folder_and_existing_native_file(self):
        self.card('claude')
        native = self.home / '.claude/projects/demo/native-123.jsonl'
        native.parent.mkdir(parents=True)
        self.hook_payload(self.env, 'claude', 'native-123', 'SessionStart', None, 0)
        self.assertEqual(self.route('--dry-run', code=4)['reason'], 'session_unavailable')
        native.write_text('UNREAD CONVERSATION\n')
        self.hook_payload(self.env, 'claude', 'native-123', 'SessionStart', self.home, 0)
        before = self.tree()
        self.assertEqual(self.route('--dry-run', code=4)['reason'], 'session_unavailable')
        self.assertEqual(self.tree(), before)

    def test_indexed_claude_folder_cannot_be_overridden_by_lifecycle_fallback(self):
        self.card('claude')
        self.native('claude', folder=self.home)
        self.hook_payload(self.env, 'claude', 'native-123', 'SessionStart', None, 0)
        self.assertEqual(self.route('--dry-run', code=4)['reason'], 'session_unavailable')

    def test_indexless_claude_rejects_ambiguous_native_files(self):
        self.card('claude')
        for directory in ('one', 'two'):
            native = self.home / '.claude/projects' / directory / 'native-123.jsonl'
            native.parent.mkdir(parents=True)
            native.write_text('UNREAD CONVERSATION\n')
        self.hook_payload(self.env, 'claude', 'native-123', 'SessionStart', None, 0)
        self.assertEqual(self.route('--dry-run', code=4)['reason'], 'session_unavailable')

    def test_indexless_claude_does_not_trust_other_provider_or_broken_log(self):
        self.card('claude')
        native = self.home / '.claude/projects/demo/native-123.jsonl'
        native.parent.mkdir(parents=True)
        native.write_text('UNREAD CONVERSATION\n')
        self.hook_payload(self.env, 'codex', 'native-123', 'SessionStart', None, 0)
        self.assertEqual(self.route('--dry-run', code=4)['reason'], 'session_unavailable')
        (self.data / 'log.csv').write_text('invalid schema\n')
        self.assertEqual(self.route('--dry-run', code=4)['reason'], 'session_unavailable')

    def test_missing_provider_never_falls_back(self):
        self.card()
        (self.binaries / 'claude').unlink()
        before = self.tree()
        result = self.route('--dry-run', code=4)
        self.assertEqual(result['reason'], 'provider_unavailable')
        self.assertEqual(result['provider'], 'claude')
        self.assertEqual(self.tree(), before)
        code, text = self.cli('work-session', '--folder', self.project, '--dry-run', human=True)
        self.assertEqual(code, 4)
        self.assertIn('--new', text)
        self.assertIn('claude', text)

    def test_wrong_folder_refuses_resume(self):
        self.card('codex')
        self.native('codex', folder=self.home)
        result = self.route('--dry-run', code=4)
        self.assertEqual(result['reason'], 'session_unavailable')

    def test_dry_run_and_invalid_configuration_do_not_mutate(self):
        before = self.tree()
        self.route('--provider', 'claude', '--dry-run', code=2)
        self.assertEqual(self.tree(), before)
        alias = self.home / 'alias'
        alias.symlink_to(self.project)
        direct = self.route('--dry-run')
        equivalent = self.command('work-session', '--folder', alias, '--dry-run')
        self.assertEqual(direct['cwd'], equivalent['cwd'])
        for config in ({'schema_version': 9}, {}, {'providers': {'installed': ['codex'], 'default': 'claude'}}):
            (self.data / 'config.json').write_text(json.dumps(config))
            before = self.tree()
            self.route('--dry-run', code=2)
            self.assertEqual(self.tree(), before)

    def test_launch_failure_preserves_owner(self):
        card = self.card()
        before = card.read_bytes()
        (self.binaries / 'osascript').unlink()  # Definite failure to start the terminal helper.
        result = self.route('--new', '--provider', 'codex', code=1)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(card.read_bytes(), before)
        attempts = json.loads(self.journal().read_text())['attempts']
        self.assertEqual(attempts[-1]['state'], 'failed')

    def test_submitted_new_session_has_no_invented_id(self):
        result = self.route()
        self.assertEqual(result['status'], 'pending')
        self.assertIsNone(result['session_id'])
        self.assertTrue(result['launch_id'])
        self.assertFalse(self.card_path().exists())
        attempts = json.loads(self.journal().read_text())['attempts']
        self.assertEqual(attempts[-1]['state'], 'submitted')
        self.assertIsNone(attempts[-1]['native_session_id'])

    def test_stale_confirmation_preserves_checkpoint(self):
        card = self.card()
        attempt = self.route('--new', '--provider', 'codex')
        self.card('claude', 'newer-checkpoint', revision=1)
        newer = card.read_bytes()
        self.hook(attempt['launch_id'])
        self.assertEqual(card.read_bytes(), newer)
        attempts = json.loads(self.journal().read_text())['attempts']
        self.assertEqual(attempts[-1]['state'], 'conflict')

    def test_competing_attempts_remain_visible(self):
        first = self.route()
        second = self.route('--new', '--provider', 'claude')
        self.assertNotEqual(first['launch_id'], second['launch_id'])
        self.assertTrue(second['possible_overlap'])
        self.hook(first['launch_id'])
        owner = self.card_path().read_bytes()
        self.hook(second['launch_id'], provider='claude')
        self.assertEqual(self.card_path().read_bytes(), owner)
        attempts = json.loads(self.journal().read_text())['attempts']
        self.assertEqual([a['state'] for a in attempts], ['confirmed', 'conflict'])

    def test_future_journal_schema_stops_before_launch(self):
        journal = self.journal()
        journal.parent.mkdir(parents=True)
        journal.write_text('{"schema_version":9,"attempts":[]}')
        capture = self.home / 'terminal-called'
        self.executable('osascript', 'from pathlib import Path\nPath(' + repr(str(capture)) + ').touch()\n')
        before = self.tree()
        self.route(code=2)
        self.assertEqual(self.tree(), before)
        self.assertFalse(capture.exists())

    def test_confirmed_native_identity_updates_owner(self):
        card = self.card()
        body = card.read_text().split('---\n', 2)[-1]
        for provider in ('codex', 'claude'):
            attempt = self.route('--new', '--provider', provider)
            self.hook(attempt['launch_id'], provider=provider, session='native-' + provider)
            metadata = self.command('card', 'locate', self.project)['metadata']
            self.assertEqual((metadata['provider'], metadata['session_id']), (provider, 'native-' + provider))
            self.assertEqual(card.read_text().split('---\n', 2)[-1], body)
            self.assertIn('name: keep-me', card.read_text())

    def test_early_hook_waits_for_successful_submission(self):
        card = self.card()
        for provider in ('claude', 'codex'):
            with self.subTest(provider=provider):
                self.simulated_native(provider)
                result = self.route('--new', '--provider', provider)
                self.assertEqual(result['status'], 'confirmed')
                self.assertEqual(result['session_id'], 'native-' + provider)
                evidence = json.loads((self.home / 'fake-native.json').read_text())
                self.assertEqual(evidence['token'], result['launch_id'])
                self.assertEqual(Path(evidence['data']).resolve(), self.data.resolve())
                self.assertEqual(Path(evidence['codex_home']).resolve(), Path(self.env['CODEX_HOME']).resolve())
                owner = self.command('card', 'locate', self.project)['metadata']
                self.assertEqual(owner['session_id'], 'native-' + provider)

    def test_early_hook_followed_by_launch_failure_keeps_old_owner(self):
        card = self.card()
        before = card.read_bytes()
        self.simulated_native('codex', fail_after=True)
        result = self.route('--new', '--provider', 'codex', code=1)
        self.assertEqual(card.read_bytes(), before)
        record = json.loads(self.journal().read_text())['attempts'][-1]
        self.assertEqual(record['state'], 'uncertain')
        self.assertEqual(record['native_session_id'], 'native-codex')
        self.assertTrue(self.route('--new', '--provider', 'claude', '--dry-run')['possible_overlap'])

    def test_unrelated_and_duplicate_hooks_cannot_steal_owner(self):
        card = self.card()
        attempt = self.route('--new', '--provider', 'codex')
        before = card.read_bytes()
        for token, provider, session, folder in (
                ('0' * 32, 'codex', 'new-native-456', self.project),
                (attempt['launch_id'], 'claude', 'new-native-456', self.project),
                (attempt['launch_id'], 'codex', '--bad', self.project),
                (attempt['launch_id'], 'codex', 'new-native-456', self.home)):
            self.hook(token, provider=provider, session=session, folder=folder)
            self.assertEqual(card.read_bytes(), before)
        self.hook(attempt['launch_id'], event='UserPromptSubmit')
        confirmed = card.read_bytes()
        self.hook(attempt['launch_id'])
        self.hook(attempt['launch_id'], session='different-session')
        self.assertEqual(card.read_bytes(), confirmed)
        self.card('claude', 'newer-owner', revision=2)
        newer = card.read_bytes()
        self.hook(attempt['launch_id'])
        self.assertEqual(card.read_bytes(), newer)

    def test_missing_hooks_leave_pending_status(self):
        result = self.route()
        code, text = self.cli('work-session', '--folder', self.project, '--new', human=True)
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'pending')
        self.assertIn('pending', text)
        self.assertIn('hook', text)
        self.assertFalse(self.card_path().exists())

    def test_session_end_preserves_attempt_history(self):
        attempt = self.route()
        self.hook(attempt['launch_id'])
        self.hook(attempt['launch_id'], event='SessionEnd')
        record = json.loads(self.journal().read_text())['attempts'][-1]
        self.assertTrue(record['ended'])
        self.assertEqual(record['native_session_id'], 'new-native-456')
        self.assertEqual(record['state'], 'confirmed')
        self.assertFalse(self.route('--new', '--dry-run')['possible_overlap'])

    def test_launch_context_preserves_literal_arguments(self):
        self.project = self.home / "Folder ' with $literal and `text`"
        self.project.mkdir()
        self.data = self.home / "Data ' $literal"
        self.env['DESKMATE_DATA_DIR'] = str(self.data)
        self.env['CODEX_HOME'] = str(self.home / "Codex ' $literal")
        self.configure()
        prompt = "Continue $checkpoint; $(touch UNWANTED) `touch UNWANTED`"
        for provider in ('claude', 'codex'):
            self.simulated_native(provider)
            result = self.route('--new', '--provider', provider, '--title', 'A " title', '--prompt', prompt)
            self.assertEqual(result['status'], 'confirmed')
            evidence = json.loads((self.home / 'fake-native.json').read_text())
            self.assertEqual(evidence['argv'][-1], prompt)
            self.assertEqual(Path(evidence['data']).resolve(), self.data.resolve())
            self.assertFalse((self.project / 'UNWANTED').exists())

    def test_invalid_title_and_environment_dry_run_leave_state_untouched(self):
        before = self.tree()
        self.route('--title', 'bad\ntitle', code=2)
        self.assertEqual(self.tree(), before)
        self.route(env={**self.env, 'DESKMATE_DRY_RUN': '1'})
        self.assertEqual(self.tree(), before)

    def test_recorded_resume_confirms_same_native_identity(self):
        revision = 0
        for provider in ('claude', 'codex'):
            self.configure('codex' if provider == 'claude' else 'claude')
            self.card(provider, revision=revision)
            self.native(provider)
            self.simulated_native(provider, native_id='native-123')
            result = self.route()
            self.assertEqual((result['mode'], result['provider'], result['status']),
                             ('resume', provider, 'confirmed'))
            self.assertEqual(result['session_id'], 'native-123')
            evidence = json.loads((self.home / 'fake-native.json').read_text())
            expected = ['--resume', 'native-123'] if provider == 'claude' else [
                'resume', '--no-daemon', '--cd', str(self.project.resolve()), '--', 'native-123']
            self.assertEqual(evidence['argv'], expected)
            revision = result['card_revision']

    def test_confirmation_recovers_partial_publication(self):
        self.card()
        attempt = self.route('--new', '--provider', 'codex')
        journal = json.loads(self.journal().read_text())
        journal['attempts'][-1].update(state='confirming', native_session_id='new-native-456')
        self.journal().write_text(json.dumps(journal))
        card = self.card('codex', 'new-native-456', revision=1)
        before = card.read_bytes()
        self.hook(attempt['launch_id'])
        self.assertEqual(card.read_bytes(), before)
        self.assertEqual(json.loads(self.journal().read_text())['attempts'][-1]['state'], 'confirmed')

    def test_concurrent_launches_keep_both_attempts_and_one_owner(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(lambda _: self.route(), range(2)))
        self.assertNotEqual(first['launch_id'], second['launch_id'])
        self.assertEqual(len(json.loads(self.journal().read_text())['attempts']), 2)
        self.hook(first['launch_id'], session='first-native')
        self.hook(second['launch_id'], session='second-native')
        owner = self.command('card', 'locate', self.project)['metadata']
        self.assertEqual(owner['session_id'], 'first-native')
        states = [a['state'] for a in json.loads(self.journal().read_text())['attempts']]
        self.assertCountEqual(states, ['confirmed', 'conflict'])

    def test_invalid_journal_record_fails_without_launch(self):
        attempt = self.route()
        path = self.journal()
        original = json.loads(path.read_text())
        for changes in ({'provider': []}, {'state': 'future-state'}, {'native_session_id': {}},
                        {'requested_session_id': 'bad'}, {'expected_revision': True}):
            journal = json.loads(json.dumps(original))
            journal['attempts'][-1].update(changes)
            path.write_text(json.dumps(journal))
            before = self.tree()
            self.route('--new', code=2)
            self.assertEqual(self.tree(), before)

    def test_late_native_hook_after_launch_error_retains_overlap_without_ownership(self):
        card = self.card()
        before = card.read_bytes()
        self.executable('osascript', 'import sys\nsys.exit(7)\n')
        attempt = self.route('--new', '--provider', 'codex', code=1)
        self.hook(attempt['launch_id'])
        record = json.loads(self.journal().read_text())['attempts'][-1]
        self.assertEqual(record['state'], 'uncertain')
        self.assertEqual(record['native_session_id'], 'new-native-456')
        self.assertEqual(card.read_bytes(), before)
        self.assertTrue(self.route('--new', '--dry-run')['possible_overlap'])
        self.hook(attempt['launch_id'], event='SessionEnd')
        self.assertFalse(self.route('--new', '--dry-run')['possible_overlap'])
        self.assertEqual(card.read_bytes(), before)

    def test_claude_legacy_folder_encoding_cannot_prove_session_ownership(self):
        self.project = self.home / 'a-b'
        self.project.mkdir()
        other = self.home / 'a_b'
        other.mkdir()
        encoded = re.sub(r'[^a-zA-Z0-9]', '-', str(other.resolve()))
        self.assertEqual(encoded, re.sub(r'[^a-zA-Z0-9]', '-', str(self.project.resolve())))
        native = self.home / '.claude/projects' / encoded / 'native-123.jsonl'
        native.parent.mkdir(parents=True)
        native.write_text(json.dumps({'type': 'user', 'cwd': str(other.resolve()),
                                      'message': {'content': 'PRIVATE synthetic content'}}) + '\n')
        self.card('claude')
        before = self.tree()
        result = self.route('--dry-run', code=4)
        self.assertEqual(result['reason'], 'session_unavailable')
        self.assertEqual(self.tree(), before)

    def test_focus_confirms_existing_identity_without_changing_owner_or_phantom_launch(self):
        card = self.card('claude')
        before = card.read_bytes()
        self.native('claude')
        self.executable('ps', "print('999 ttys777 claude --resume native-123')\n")
        self.executable('osascript', "print('focused')\n")
        for _ in range(2):
            result = self.route()
            self.assertEqual(result['status'], 'focused')
            self.assertEqual(result['session_id'], 'native-123')
            self.assertEqual(card.read_bytes(), before)
        attempts = json.loads(self.journal().read_text())['attempts']
        self.assertTrue(all(a['state'] == 'confirmed' and a['native_session_id'] == 'native-123'
                            for a in attempts))
        self.assertEqual(len(self.route('--dry-run')['possible_overlap']), 1)
        # The existing process never received the new correlation IDs.
        self.hook_payload(self.env, 'claude', 'native-123', 'SessionEnd', self.project, 0)
        self.assertFalse(self.route('--dry-run')['possible_overlap'])
        self.assertTrue(all(a['ended'] for a in json.loads(self.journal().read_text())['attempts']))
        self.assertEqual(card.read_bytes(), before)

    def test_terminal_submission_error_keeps_uncertain_overlap_even_without_hooks(self):
        card = self.card()
        before = card.read_bytes()
        self.executable('osascript', 'import sys\nsys.exit(7)\n')
        for provider in ('claude', 'codex'):
            result = self.route('--new', '--provider', provider, code=1)
            self.assertEqual(result['reason'], 'launch_uncertain')
            self.assertEqual(card.read_bytes(), before)
        attempts = json.loads(self.journal().read_text())['attempts']
        self.assertTrue(all(a['state'] == 'uncertain' for a in attempts))
        self.assertEqual(len(self.route('--new', '--dry-run')['possible_overlap']), 2)


if __name__ == '__main__':
    unittest.main()
