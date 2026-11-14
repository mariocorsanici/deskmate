"""Provider launch through a different iTerm profile, using only fake native CLIs."""
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LaunchEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "Selected ' home"
        self.home.mkdir()
        self.project = self.home / 'Project'
        self.project.mkdir()
        self.data = self.home / 'data'
        self.data.mkdir()
        (self.data / 'config.json').write_text(json.dumps({
            'schema_version': 1, 'providers': {'installed': ['claude', 'codex'], 'default': 'claude'}}))
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        self.profile = self.base / 'Profile home'
        self.profile.mkdir()
        self.profile_bin = self.profile / 'bin'
        self.profile_bin.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home), 'PATH': str(self.bin),
                    'CODEX_HOME': str(self.home / "Codex ' config"),
                    'DESKMATE_DATA_DIR': str(self.data), 'PYTHONDONTWRITEBYTECODE': '1',
                    'UNRELATED_MARKER': 'CALLER_CANARY_MUST_NOT_BE_SERIALIZED'}
        for key in ('CLAUDE_CONFIG_DIR', 'DESKMATE_LAUNCH_ID', 'DESKMATE_DRY_RUN'):
            self.env.pop(key, None)
        for provider in ('claude', 'codex'):
            capture = str(self.home / (provider + '-capture.json'))
            hook = [sys.executable, str(ROOT / 'bin/deskmate'), 'hook-event', '--provider', provider]
            body = ("import json,os,subprocess,sys\nfrom pathlib import Path\n"
                    "if '--version' in sys.argv: print('" + provider + " 1.0.0'); sys.exit(0)\n"
                    "payload={'hook_event_name':'SessionStart','session_id':'native-" + provider + "','cwd':os.getcwd()}\n"
                    "r=subprocess.run(" + repr(hook) + ",input=json.dumps(payload),capture_output=True,text=True)\n"
                    "if r.returncode: sys.stderr.write(r.stderr); sys.exit(r.returncode)\n"
                    "Path(" + repr(capture) + ").write_text(json.dumps({'executable':sys.argv[0],'argv':sys.argv[1:],"
                    "'cwd':os.getcwd(),'environment':{k:os.environ.get(k) for k in "
                    "['HOME','PATH','CLAUDE_CONFIG_DIR','CODEX_HOME','DESKMATE_DATA_DIR','DESKMATE_LAUNCH_ID','UNRELATED_MARKER']}}))\n")
            self.executable(self.bin / provider, body)
            self.executable(self.profile_bin / provider,
                            "from pathlib import Path\nPath(" + repr(str(self.profile / 'wrong-cli')) + ").touch()\n")
        self.executable(self.bin / 'ps', 'import sys\nsys.exit(0)\n')
        profile_env = {'HOME': str(self.profile), 'PATH': str(self.profile_bin),
                       'ZDOTDIR': str(self.profile),
                       'CODEX_HOME': str(self.profile / '.codex'),
                       'CLAUDE_CONFIG_DIR': str(self.profile / '.claude'),
                       'DESKMATE_DATA_DIR': str(self.profile / 'data'),
                       'DESKMATE_LAUNCH_ID': 'f' * 32, 'UNRELATED_MARKER': 'PROFILE'}
        self.executable(self.bin / 'osascript',
                        "import json,os,subprocess,sys\nfrom pathlib import Path\n"
                        "script=sys.stdin.read()\n"
                        "Path(" + repr(str(self.home / 'transport.json')) + ").write_text(json.dumps({'command':sys.argv[2],'script':script}))\n"
                        "env=dict(os.environ); env.update(" + repr(profile_env) + ")\n"
                        "r=subprocess.run(['/bin/sh','-c',sys.argv[2]],env=env,capture_output=True,text=True)\n"
                        "sys.stderr.write(r.stderr); sys.exit(r.returncode)\n")

    def executable(self, path, body):
        path.write_text('#!' + sys.executable + '\n' + body)
        path.chmod(0o755)

    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'bin/deskmate'), *map(str, args)],
                              env=self.env, cwd=self.home, capture_output=True, text=True, timeout=15)

    def native_session(self, provider):
        if provider == 'claude':
            config = Path(self.env.get('CLAUDE_CONFIG_DIR', self.home / '.claude'))
            directory = config / 'projects/demo'
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'sessions-index.json').write_text(json.dumps({'entries': [{
                'sessionId': 'native-claude', 'projectPath': str(self.project),
                'created': '2026-11-13T10:00:00Z', 'modified': '2026-11-13T10:00:00Z'}]}))
            (directory / 'native-claude.jsonl').write_text('UNREAD CONVERSATION\n')
        else:
            directory = Path(self.env['CODEX_HOME']) / 'sessions'
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'rollout-native-codex.jsonl').write_text(json.dumps({
                'type': 'session_meta', 'timestamp': '2026-11-13T10:00:00Z',
                'payload': {'id': 'native-codex', 'cwd': str(self.project)}}) + '\n')
        candidate = self.home / 'candidate.md'
        candidate.write_text('# Fixture\n\n## Status\nActive\n')
        r = self.cli('card', 'write', self.project, '--provider', provider,
                     '--session-id', 'native-' + provider, '--expected-revision', '0', '--from', candidate)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def check_launch(self, provider, resume=False, expected_environment=None, expected_marker='PROFILE'):
        if resume:
            self.native_session(provider)
        args = [] if resume else ['--new', '--provider', provider]
        r = self.cli('--json', 'work-session', '--folder', self.project, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        result = json.loads(json.loads(r.stdout)['stdout'])
        self.assertEqual(result['status'], 'confirmed', result)
        self.assertEqual(result['session_id'], 'native-' + provider)
        capture = json.loads((self.home / (provider + '-capture.json')).read_text())
        env = capture['environment']
        self.assertEqual(capture['executable'], str(self.bin / provider))
        self.assertEqual(capture['cwd'], str(self.project))
        self.assertEqual(env['HOME'], str(self.home))
        expected = {'PATH': self.env['PATH'],
                    'CODEX_HOME': self.env.get('CODEX_HOME', str(self.home / '.codex')),
                    'CLAUDE_CONFIG_DIR': self.env.get('CLAUDE_CONFIG_DIR')}
        expected.update(expected_environment or {})
        self.assertEqual(env['PATH'], expected['PATH'])
        self.assertEqual(env['CODEX_HOME'], expected['CODEX_HOME'])
        self.assertEqual(env['DESKMATE_DATA_DIR'], str(self.data))
        self.assertEqual(env['CLAUDE_CONFIG_DIR'], expected['CLAUDE_CONFIG_DIR'])
        self.assertEqual(env['DESKMATE_LAUNCH_ID'], result['launch_id'])
        self.assertEqual(env['UNRELATED_MARKER'], expected_marker)
        self.assertFalse((self.profile / 'wrong-cli').exists())
        transport = json.loads((self.home / 'transport.json').read_text())
        self.assertNotIn('CALLER_CANARY', transport['command'])
        return capture

    def test_new_claude_uses_selected_environment_in_a_different_profile(self):
        self.check_launch('claude')

    def test_new_codex_uses_selected_environment_in_a_different_profile(self):
        self.check_launch('codex')

    def test_claude_resume_uses_explicit_configuration(self):
        self.env['CLAUDE_CONFIG_DIR'] = str(self.home / "Claude ' config")
        self.check_launch('claude', resume=True)

    def test_codex_resume_keeps_selected_native_storage(self):
        self.check_launch('codex', resume=True)

    def check_codex_with_stale_daemon(self, resume=False):
        """A shared server keeps its startup environment across CLI launches."""
        executable = self.bin / 'codex'
        source = executable.read_text()
        stale_data = self.profile / 'stale-daemon-data'
        stale = {'HOME': str(self.profile), 'DESKMATE_DATA_DIR': str(stale_data),
                 'DESKMATE_LAUNCH_ID': 'd' * 32, 'CODEX_HOME': str(self.profile / '.codex')}
        boundary = "payload={'hook_event_name':'SessionStart'"
        self.assertIn(boundary, source)
        source = source.replace(boundary,
            "if '--no-daemon' not in sys.argv:\n    os.environ.update(" + repr(stale) + ")\n" + boundary)
        executable.write_text(source)
        self.check_launch('codex', resume=resume)
        self.assertFalse(stale_data.exists(), 'Hooks wrote into the shared daemon data root')

    def test_new_codex_keeps_its_own_environment_when_a_stale_daemon_exists(self):
        self.check_codex_with_stale_daemon()

    def test_codex_resume_keeps_its_own_environment_when_a_stale_daemon_exists(self):
        self.check_codex_with_stale_daemon(resume=True)

    def test_default_storage_and_unset_claude_config_override_profile_values(self):
        self.env.pop('CODEX_HOME')
        self.check_launch('claude')

    def test_relative_paths_keep_their_meaning_after_changing_project_directory(self):
        self.env.update(PATH='bin', CODEX_HOME="Codex ' config", CLAUDE_CONFIG_DIR="Claude ' config")
        self.check_launch('claude', expected_environment={
            'PATH': str(self.bin), 'CODEX_HOME': str(self.home / "Codex ' config"),
            'CLAUDE_CONFIG_DIR': str(self.home / "Claude ' config")})

    def test_selected_executable_keeps_its_symlink_name(self):
        selected = self.bin / 'claude'
        target = self.home / 'actual-native-runner'
        target.write_bytes(selected.read_bytes())
        target.chmod(0o755)
        selected.unlink()
        selected.symlink_to(target)
        self.check_launch('claude')

    def test_missing_selected_cli_never_uses_the_terminal_profiles_cli(self):
        (self.bin / 'claude').unlink()
        r = self.cli('--json', 'provider-launch', '--provider', 'claude', '--folder', self.project)
        self.assertNotEqual(r.returncode, 0)
        envelope = json.loads(r.stdout)
        self.assertEqual(json.loads(envelope['stdout'])['status'], 'error')
        self.assertFalse((self.home / 'transport.json').exists())

    def test_provider_launch_clears_stale_profile_correlation(self):
        r = self.cli('provider-launch', '--provider', 'codex', '--folder', self.project)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        capture = json.loads((self.home / 'codex-capture.json').read_text())
        self.assertIsNone(capture['environment']['DESKMATE_LAUNCH_ID'])

    def test_invalid_native_configuration_is_rejected_before_submission(self):
        self.env['CODEX_HOME'] = ''
        r = self.cli('--json', 'provider-launch', '--provider', 'codex', '--folder', self.project)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(json.loads(r.stdout)['stdout'])['status'], 'error')
        self.assertFalse((self.home / 'transport.json').exists())

    def test_selected_shell_startup_is_kept_without_overriding_the_verified_paths(self):
        (self.home / '.zshrc').write_text(
            "export UNRELATED_MARKER=SELECTED_STARTUP\nexport PATH=/wrong/profile/bin\n"
            'export HOME=' + shlex.quote(str(self.profile)) + '\n'
            'export CODEX_HOME=' + shlex.quote(str(self.profile / '.codex')) + '\n'
            'export CLAUDE_CONFIG_DIR=' + shlex.quote(str(self.profile / '.claude')) + '\n')
        self.check_launch('claude', expected_marker='SELECTED_STARTUP')

    def test_explicit_zdotdir_selects_the_callers_shell_configuration(self):
        directory = self.home / 'Selected shell configuration'
        directory.mkdir()
        (directory / '.zshrc').write_text('export UNRELATED_MARKER=SELECTED_ZDOTDIR\n')
        self.env['ZDOTDIR'] = str(directory)
        self.check_launch('claude', expected_marker='SELECTED_ZDOTDIR')
