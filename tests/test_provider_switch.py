"""Provider switch acceptance with isolated state and actual CLI/PTY boundaries."""
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import time
import unittest
from tests import test_work_sessions as fixtures

ROOT = Path(__file__).resolve().parents[1]


class ProviderSwitchTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkSessionsTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.home, self.project = self.fixture.home, self.fixture.project
        self.data, self.env = self.fixture.data, self.fixture.env
        self.card = self.fixture.card()

    def preview(self, target='codex', code=0):
        return self.fixture.command('switch', '--folder', self.project, '--to', target,
                                    '--preview', code=code)

    def interactive(self, answer, target='codex'):
        master, slave = pty.openpty()
        process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'bin/deskmate'),
                                    'switch', '--folder', str(self.project), '--to', target],
                                   env=self.env, stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        output = b''
        sent = False
        deadline = time.monotonic() + 20
        try:
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output += chunk
                    if b'Confirm transfer' in output and not sent:
                        reply = answer() if callable(answer) else answer
                        os.write(master, reply.encode() + b'\n')
                        sent = True
                if process.poll() is not None:
                    break
            if process.poll() is None:
                process.kill()
                self.fail('Interactive switch did not terminate: ' + output.decode(errors='replace'))
            return process.wait(), output.decode(errors='replace')
        finally:
            os.close(master)
            if process.poll() is None:
                process.kill()
            process.wait()

    def test_preview_switches_both_directions_without_source_provider_or_transcript(self):
        for source, target, revision in [('claude', 'codex', 1), ('codex', 'claude', 2)]:
            with self.subTest(source=source):
                if source == 'codex':
                    self.fixture.card(source, revision=1)
                    self.fixture.executable('claude', "print('claude 1.0.0')\n")
                (self.fixture.binaries / source).unlink()
                before = self.fixture.tree()
                result = self.preview(target)
                self.assertEqual(result['source_provider'], source)
                self.assertEqual(result['provider'], target)
                self.assertEqual(result['mode'], 'new')
                self.assertIsNone(result['session_id'])
                self.assertEqual(result['card_revision'], revision)
                self.assertTrue(result['warnings'])
                self.assertTrue(result['possible_overlap'])
                self.assertEqual(self.fixture.tree(), before)

    def test_cancellation_warns_about_overlap_and_changes_no_state(self):
        before = self.fixture.tree()
        code, output = self.interactive('no')
        self.assertEqual(code, 0, output)
        self.assertIn('simultaneous', output.lower())
        self.assertIn('cancelled', output.lower())
        self.assertEqual(self.fixture.tree(), before)

    def test_noninteractive_switch_cannot_be_confirmed_by_piped_input(self):
        before = self.fixture.tree()
        code, envelope = self.fixture.cli('switch', '--folder', self.project, '--to', 'codex',
                                          human=False)
        self.assertEqual(code, 4, envelope)
        self.assertEqual(self.fixture.tree(), before)

    def test_same_provider_is_not_a_switch_and_missing_target_is_refused(self):
        self.preview('claude', code=2)
        (self.fixture.binaries / 'codex').unlink()
        self.preview('codex', code=1)

    def test_target_receives_current_checks_via_private_path_and_new_native_identity(self):
        source = self.home / 'candidate.md'
        source.write_text('# Demo\n## Status\nUNSAVED_CARD_CANARY\n## Checks\n- live: `printf CURRENT_CHECK`\n')
        self.fixture.command('card', 'write', self.project, '--expected-revision', 1,
                             '--provider', 'claude', '--session-id', 'native-123', '--from', source)
        self.fixture.simulated_native('codex', native_id='new-native-codex')
        code, output = self.interactive('yes')
        self.assertEqual(code, 0, output)
        native = json.loads((self.home / 'fake-native.json').read_text())
        self.assertNotIn('resume', native['argv'])
        self.assertNotIn('UNSAVED_CARD_CANARY', json.dumps(native))
        self.assertNotIn('CURRENT_CHECK', json.dumps(native))
        located = self.fixture.command('card', 'locate', self.project)['metadata']
        self.assertEqual((located['provider'], located['session_id']), ('codex', 'new-native-codex'))
        bundles = list((self.data / 'transfers').glob('transfer-*.json'))
        self.assertEqual(len(bundles), 1)
        self.assertEqual(bundles[0].stat().st_mode & 0o777, 0o600)
        body = bundles[0].read_text()
        self.assertIn('UNSAVED_CARD_CANARY', body)
        self.assertIn('CURRENT_CHECK', body)
        self.assertIn('missing', body.lower())

    def test_target_launch_failure_keeps_source_ownership(self):
        before = self.card.read_bytes()
        self.fixture.executable('osascript', 'import sys\nsys.exit(7)\n')
        code, output = self.interactive('yes')
        self.assertEqual(code, 1, output)
        self.assertEqual(self.card.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
