"""Public launch contracts at the iTerm/process boundary, without opening a GUI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import signal
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class TerminalLaunchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.folder = self.home / "Project ' with spaces"
        self.folder.mkdir()
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        self.launch_tmp = self.home / 'launch-tmp'
        self.launch_tmp.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home),
                    'CODEX_HOME': str(self.home / '.codex'),
                    'DESKMATE_DATA_DIR': str(self.home / 'data'),
                    'TMPDIR': str(self.launch_tmp), 'PYTHONDONTWRITEBYTECODE': '1',
                    'PATH': str(self.bin), 'C15_PROCESS': 'present'}
        for key in ('CLAUDE_CONFIG_DIR', 'DESKMATE_DRY_RUN', 'DESKMATE_LAUNCH_ID'):
            self.env.pop(key, None)
        for provider in ('claude', 'codex'):
            self.executable(provider,
                "import json,os,sys\nfrom pathlib import Path\n"
                "Path(os.environ['HOME'],'native.json').write_text(json.dumps({'argv':sys.argv[1:],'cwd':os.getcwd()}))\n")
        self.executable('osascript',
            "import json,os,subprocess,sys\nfrom pathlib import Path\n"
            "home=Path(os.environ['HOME']); script=sys.stdin.read()\n"
            "files=[{'path':str(p),'mode':p.stat().st_mode & 0o777,'parent_mode':p.parent.stat().st_mode & 0o777} "
            "for p in Path(os.environ['TMPDIR']).glob('deskmate-launch-*/payload.json')]\n"
            "(home/'terminal.json').write_text(json.dumps({'args':sys.argv[1:],'script':script,'payloads':files}))\n"
            "r=subprocess.run(['/bin/zsh','-c',sys.argv[2]],capture_output=True,text=True)\n"
            "sys.stderr.write(r.stderr)\n"
            "print('/dev/ttys042\\tC15-TEST-SESSION')\n"
            "sys.exit(r.returncode)\n")
        self.executable('ps',
            "import os,sys\nfrom pathlib import Path\n"
            "if '-t' not in sys.argv: sys.exit(0)\n"
            "with Path(os.environ['HOME'],'ps-calls.txt').open('a') as f: f.write(repr(sys.argv[1:])+'\\n')\n"
            "if os.environ['C15_PROCESS']=='present': print('4242 '+str(Path(os.environ['HOME'],'bin',os.environ['C15_PROVIDER'])))\n"
            "elif os.environ['C15_PROCESS']=='wrong': print('4343 /unrelated/bin/other-provider')\n")

    def executable(self, name, source):
        path = self.bin / name
        path.write_text('#!' + sys.executable + '\n' + source)
        path.chmod(0o755)

    def launch(self, provider, *extra, process='present'):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'bin/deskmate'),
                                 '--json', 'provider-launch', '--provider', provider,
                                 '--folder', str(self.folder), *extra],
                                env={**self.env, 'C15_PROVIDER': provider, 'C15_PROCESS': process},
                                capture_output=True, text=True, timeout=20)
        self.assertNotIn('Traceback', result.stdout + result.stderr)
        envelope = json.loads(result.stdout)
        return result.returncode, json.loads(envelope['stdout'])

    def native(self, provider):
        if provider == 'claude':
            directory = self.home / '.claude/projects/example'
            directory.mkdir(parents=True)
            (directory / 'sessions-index.json').write_text(json.dumps({'entries': [{
                'sessionId': 'native-123', 'projectPath': str(self.folder),
                'created': '2026-11-15T10:00:00Z', 'modified': '2026-11-15T10:01:00Z'}]}))
            (directory / 'native-123.jsonl').write_text('UNREAD_CONVERSATION\n')
        else:
            directory = self.home / '.codex/sessions'
            directory.mkdir(parents=True)
            (directory / 'rollout-native-123.jsonl').write_text(json.dumps({
                'type': 'session_meta', 'timestamp': '2026-11-15T10:00:00Z',
                'payload': {'id': 'native-123', 'cwd': str(self.folder)}}) + '\n')

    def test_long_quoted_multiline_prompt_is_private_and_delivered_literally(self):
        prompt = ('UNIQUE_PROMPT_CANARY "quotes" $HOME `touch UNWANTED` $(touch UNWANTED)\n' * 40)
        for provider in ('claude', 'codex'):
            with self.subTest(provider=provider):
                code, result = self.launch(provider, '--prompt', prompt)
                self.assertEqual(code, 0, result)
                terminal = json.loads((self.home / 'terminal.json').read_text())
                self.assertNotIn('UNIQUE_PROMPT_CANARY', json.dumps(terminal['args']))
                self.assertEqual(len(terminal['payloads']), 1)
                self.assertEqual(terminal['payloads'][0]['mode'], 0o600)
                self.assertEqual(terminal['payloads'][0]['parent_mode'], 0o700)
                self.assertFalse(Path(terminal['payloads'][0]['path']).exists())
                received = json.loads((self.home / 'native.json').read_text())
                self.assertEqual(received['argv'][-1], prompt)
                self.assertEqual(received['cwd'], str(self.folder))
                self.assertFalse((self.folder / 'UNWANTED').exists())

    def test_launch_reports_the_matching_process_in_the_returned_tty(self):
        for provider in ('claude', 'codex'):
            with self.subTest(provider=provider):
                code, result = self.launch(provider)
                self.assertEqual(code, 0, result)
                self.assertEqual(result.get('tty'), '/dev/ttys042')
                self.assertEqual(result.get('pid'), 4242)
                self.assertEqual(result.get('terminal_session_id'), 'C15-TEST-SESSION')
                self.assertIn('ttys042', (self.home / 'ps-calls.txt').read_text())

    def test_missing_or_wrong_provider_process_is_an_actionable_error(self):
        for provider, process in [('claude', 'missing'), ('codex', 'wrong')]:
            with self.subTest(provider=provider, process=process):
                code, result = self.launch(provider, process=process)
                self.assertNotEqual(code, 0, result)
                self.assertEqual(result['status'], 'error')
                self.assertEqual(result.get('tty'), '/dev/ttys042')
                warnings = ' '.join(result['warnings'])
                self.assertIn(provider, warnings)
                self.assertIn('/dev/ttys042', warnings)
                self.assertIn('C15-TEST-SESSION', warnings)
                self.assertFalse(list(self.launch_tmp.glob('deskmate-launch-*/payload.json')))

    def test_resume_receives_the_same_process_verification(self):
        for provider in ('claude', 'codex'):
            with self.subTest(provider=provider):
                self.native(provider)
                code, result = self.launch(provider, '--session-id', 'native-123')
                self.assertEqual(code, 0, result)
                self.assertEqual(result['mode'], 'resume')
                self.assertEqual(result['session_id'], 'native-123')
                self.assertEqual(result.get('pid'), 4242)
                self.assertEqual(result.get('tty'), '/dev/ttys042')

    def test_dry_run_never_creates_payload_or_submits_a_terminal(self):
        for provider in ('claude', 'codex'):
            code, result = self.launch(provider, '--dry-run', '--prompt', 'PRIVATE_DRY_RUN')
            self.assertEqual(code, 0, result)
        self.assertFalse((self.home / 'terminal.json').exists())
        self.assertFalse(list(self.launch_tmp.iterdir()))

    def test_process_inspection_timeout_retains_the_tab_diagnostics(self):
        self.executable('ps', 'import time\ntime.sleep(3)\n')
        code, result = self.launch('codex')
        self.assertNotEqual(code, 0, result)
        self.assertEqual(result.get('tty'), '/dev/ttys042')
        self.assertEqual(result.get('terminal_session_id'), 'C15-TEST-SESSION')

    def test_selected_script_accepts_the_resolved_shebang_interpreter(self):
        real = Path(sys.executable).resolve()
        alias = self.bin / 'native-python'
        alias.symlink_to(real)
        native = self.bin / 'codex'
        body = native.read_text().split('\n', 1)[1]
        native.write_text('#!' + str(alias) + '\n' + body)
        self.executable('ps',
            "import sys\n"
            "if '-t' in sys.argv: print('4242 '+" + repr(str(real)) + ")\n"
            "elif '-p' in sys.argv: print(" + repr(str(real) + ' ' + str(native)) + ")\n")
        code, result = self.launch('codex')
        self.assertEqual(code, 0, result)
        self.assertEqual(result.get('pid'), 4242)

    def test_env_split_string_interpreter_options_keep_the_selected_script_identity(self):
        real = Path(sys.executable).resolve()
        native = self.bin / 'codex'
        body = native.read_text().split('\n', 1)[1]
        native.write_text('#!/usr/bin/env -S ' + str(real) + ' -B\n' + body)
        self.executable('ps',
            "import sys\n"
            "if '-t' in sys.argv: print('4242 '+" + repr(str(real)) + ")\n"
            "elif '-p' in sys.argv: print(" + repr(str(real) + ' -B ' + str(native)) + ")\n")
        code, result = self.launch('codex')
        self.assertEqual(code, 0, result)
        self.assertEqual(result.get('pid'), 4242)

    def test_slow_script_process_lookups_share_one_startup_deadline(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import terminal_launch
        clock = [0.0]

        def run(args, **kwargs):
            if '-t' in args:
                clock[0] += 0.02
                rows = ''.join(str(pid) + ' ' + sys.executable + '\n' for pid in (42, 43, 44))
                return subprocess.CompletedProcess(args, 0, rows, '')
            delay = 0.09
            clock[0] += min(delay, kwargs['timeout'])
            if kwargs['timeout'] < delay:
                raise subprocess.TimeoutExpired(args, kwargs['timeout'])
            return subprocess.CompletedProcess(args, 0, sys.executable + ' /unrelated/script.py', '')

        with patch.object(terminal_launch.time, 'monotonic', lambda: clock[0]), \
                patch.object(terminal_launch.time, 'sleep', lambda delay: clock.__setitem__(0, clock[0] + delay)), \
                patch.object(terminal_launch.subprocess, 'run', run):
            result = terminal_launch.wait_for_process(self.bin / 'codex', '/dev/ttys042', timeout=0.1)
        self.assertIsNone(result)
        self.assertLessEqual(clock[0], 0.100001)

    def test_interrupted_terminal_submission_removes_the_private_prompt(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import terminal_launch
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(terminal_launch.tempfile, 'tempdir', str(self.launch_tmp)), \
                patch.object(terminal_launch.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                terminal_launch.start([str(self.bin / 'codex'), 'PRIVATE_INTERRUPT_CANARY'],
                                      'codex', self.folder, ROOT, 'Interrupted test')
        self.assertFalse(list(self.launch_tmp.glob('deskmate-launch-*/payload.json')))
        self.assertFalse(list(self.launch_tmp.iterdir()))

    def test_terminating_the_runner_reaps_its_child_without_waiting_for_input(self):
        import pty
        self.executable('codex',
            "import os,time\nfrom pathlib import Path\n"
            "Path(os.environ['HOME'],'sleep-child.pid').write_text(str(os.getpid()))\n"
            "time.sleep(30)\n")
        directory = self.launch_tmp / 'deskmate-launch-term'
        directory.mkdir(mode=0o700)
        payload = directory / 'payload.json'
        payload.write_text(json.dumps({'schema_version': 1, 'provider': 'codex',
                                       'cwd': str(self.folder), 'argv': [str(self.bin / 'codex')]}))
        payload.chmod(0o600)
        master, slave = pty.openpty()
        runner = subprocess.Popen([sys.executable, '-B', str(ROOT / 'tools/terminal_launch.py'),
                                   '--payload', str(payload)], stdin=slave, stdout=slave, stderr=slave,
                                  env=self.env, start_new_session=True)
        child_pid = None
        try:
            deadline = time.monotonic() + 5
            while not (self.home / 'sleep-child.pid').exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.home / 'sleep-child.pid').exists())
            child_pid = int((self.home / 'sleep-child.pid').read_text())
            runner.send_signal(signal.SIGTERM)
            try:
                code = runner.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.fail('Terminated runner stayed alive waiting for terminal input')
            self.assertNotEqual(code, 0)
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)
            self.assertFalse(directory.exists())
        finally:
            if runner.poll() is None:
                runner.kill()
            runner.wait(timeout=5)
            if child_pid is not None:
                try:
                    os.kill(child_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    unittest.main()
