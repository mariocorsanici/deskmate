"""Routing acceptance through the public command, with no native model calls."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
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
        self.executable('osascript', 'import sys\nsys.exit(7)\n')
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


if __name__ == '__main__':
    unittest.main()
