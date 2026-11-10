"""Consent/redaction/bundle lifecycle tests; secrets are synthetic canaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from tests import test_provider_switch as switch_fixtures

ROOT = Path(__file__).resolve().parents[1]
CANARY = 'sk-test-SYNTHETICCANARYONLY123456789'


class TransfersTest(unittest.TestCase):
    def setUp(self):
        self.switch = switch_fixtures.ProviderSwitchTest()
        self.switch.setUp()
        self.addCleanup(self.switch.doCleanups)
        self.fixture = self.switch.fixture
        self.home, self.data, self.project = self.switch.home, self.switch.data, self.switch.project

    def card(self, content):
        candidate = self.home / 'secret-candidate.md'
        candidate.write_text('# Demo\n## Status\n' + content + '\n## Checks\n')
        self.fixture.command('card', 'write', self.project, '--expected-revision', 1,
                             '--provider', 'claude', '--session-id', 'native-123', '--from', candidate)

    def launch(self):
        self.fixture.simulated_native('codex', native_id='target-session')
        code, output = self.switch.interactive('yes')
        self.assertEqual(code, 0, output)
        bundles = list((self.data / 'transfers').glob('transfer-*.json'))
        self.assertEqual(len(bundles), 1)
        return bundles[0]

    def test_preview_reports_redactions_and_never_discloses_secret_values(self):
        self.card('api_key=' + CANARY)
        before = self.fixture.tree()
        result = self.switch.preview()
        self.assertGreaterEqual(result['manifest']['redactions'].get('credential', 0), 1)
        self.assertEqual(result['manifest']['source_provider'], 'claude')
        self.assertEqual(result['manifest']['target_provider'], 'codex')
        self.assertGreater(result['manifest']['bytes'], 0)
        self.assertNotIn(CANARY, json.dumps(result))
        self.assertEqual(self.fixture.tree(), before)

    def test_bounded_native_delta_is_redacted_before_preview_and_transfer(self):
        directory = self.home / '.claude/projects/delta'
        directory.mkdir(parents=True)
        (directory / 'native-123.jsonl').write_text(json.dumps({
            'type': 'user', 'cwd': str(self.project), 'timestamp': '2026-11-09T10:00:00Z',
            'message': {'content': 'Recent api_key=' + CANARY}}) + '\n')
        result = self.switch.preview()
        self.assertEqual(result['manifest']['delta']['included_messages'], 1)
        self.assertGreaterEqual(result['manifest']['redactions'].get('credential', 0), 1)
        self.assertNotIn(CANARY, json.dumps(result))
        path = self.launch()
        self.assertNotIn(CANARY, path.read_text())
        self.assertIn('Recent', path.read_text())

    def test_unclosed_private_key_blocks_transfer_without_exposing_content(self):
        self.card('-----BEGIN PRIVATE KEY-----\nSYNTHETIC_UNCLOSED_PRIVATE_CANARY')
        before = self.fixture.tree()
        result = self.switch.preview(code=4)
        self.assertEqual(result['reason'], 'uncertain_secret')
        self.assertGreater(result['manifest']['blocked_findings'], 0)
        self.assertNotIn('SYNTHETIC_UNCLOSED_PRIVATE_CANARY', json.dumps(result))
        self.assertEqual(self.fixture.tree(), before)

    def test_approved_bundle_is_redacted_audit_is_content_free_and_consumption_deletes(self):
        self.card('api_key=' + CANARY)
        preview = self.switch.preview()
        path = self.launch()
        self.assertEqual(path.stat().st_size, preview['manifest']['bytes'])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        self.assertNotIn(CANARY, path.read_text())
        native = json.loads((self.home / 'fake-native.json').read_text())
        self.assertIn(str(path), json.dumps(native['argv']))
        self.assertNotIn(CANARY, json.dumps(native))
        log = (self.data / 'log.csv').read_text()
        self.assertIn('provider-switch', log)
        self.assertNotIn(CANARY, log)
        self.assertNotIn('api_key=', log)
        result = self.fixture.command('transfer-read', '--bundle', path, '--provider', 'codex')
        self.assertEqual(result['target_provider'], 'codex')
        self.assertNotIn(CANARY, json.dumps(result))
        self.assertFalse(path.exists())

    def test_wrong_target_and_symlink_reads_preserve_bundle_and_unrelated_data(self):
        path = self.launch()
        self.fixture.command('transfer-read', '--bundle', path, '--provider', 'claude', code=2)
        self.assertTrue(path.exists())
        unrelated = self.home / 'unrelated.json'
        unrelated.write_text('UNRELATED_CONTENT')
        linked = path.parent / 'transfer-symlink.json'
        linked.symlink_to(unrelated)
        self.fixture.command('transfer-read', '--bundle', linked, '--provider', 'codex', code=2)
        self.assertEqual(unrelated.read_text(), 'UNRELATED_CONTENT')
        self.assertTrue(linked.is_symlink())

    def test_orphan_cleanup_removes_only_expired_managed_regular_bundles(self):
        path = self.launch()
        old = time.time() - 3700
        os.utime(path, (old, old))
        unrelated = path.parent / 'notes.json'
        unrelated.write_text('KEEP')
        os.utime(unrelated, (old, old))
        linked = path.parent / 'transfer-linked.json'
        linked.symlink_to(unrelated)
        result = self.fixture.command('transfer-cleanup')
        self.assertEqual(result['removed'], 1)
        self.assertFalse(path.exists())
        self.assertEqual(unrelated.read_text(), 'KEEP')
        self.assertTrue(linked.is_symlink())

    def test_interrupted_bundle_write_is_expired_without_removing_unrelated_files(self):
        script = ("import json,os,sys\nfrom pathlib import Path\n"
                  "sys.path.insert(0, sys.argv[1])\nimport transfers\n"
                  "def interrupted_dump(body, stream):\n"
                  "    stream.write('{\"private\": \"INTERRUPTED_CONTEXT_CANARY'); stream.flush(); os._exit(71)\n"
                  "transfers.json.dump = interrupted_dump\n"
                  "transfers.create({'schema_version':1,'source_provider':'claude',"
                  "'target_provider':'codex','card_id':'demo'})\n")
        result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'tools')],
                                env=self.fixture.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 71, result.stderr)
        parent = self.data / 'transfers'
        files = list(parent.iterdir())
        self.assertEqual(len(files), 1)
        interrupted = files[0]
        self.assertIn('INTERRUPTED_CONTEXT_CANARY', interrupted.read_text())
        old = time.time() - 3700
        os.utime(interrupted, (old, old))
        unrelated = parent / 'notes.json'
        unrelated.write_text('KEEP')
        linked = parent / ('.pending-transfer-' + 'f' * 32 + '.json')
        linked.symlink_to(unrelated)
        hardlinked = parent / ('.pending-transfer-' + 'e' * 32 + '.json')
        os.link(unrelated, hardlinked)
        os.utime(unrelated, (old, old))
        output = self.fixture.command('transfer-cleanup')
        self.assertEqual(output['removed'], 1)
        self.assertFalse(interrupted.exists())
        self.assertEqual(unrelated.read_text(), 'KEEP')
        self.assertTrue(linked.is_symlink())
        self.assertTrue(hardlinked.is_file())

    def test_cleanup_preserves_active_staging_writer_then_expires_its_abandoned_file(self):
        import select
        script = ("import os,sys\nsys.path.insert(0, sys.argv[1])\nimport transfers\n"
                  "def paused_dump(body, stream):\n"
                  "    stream.write('PARTIAL_ACTIVE_CONTEXT'); stream.flush()\n"
                  "    print('ready', flush=True); sys.stdin.readline(); os._exit(71)\n"
                  "transfers.json.dump = paused_dump\ntransfers.create({})\n")
        process = subprocess.Popen([sys.executable, '-c', script, str(ROOT / 'tools')],
                                   env=self.fixture.env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([process.stdout], [], [], 10)[0])
            self.assertEqual(process.stdout.readline().strip(), 'ready')
            staged = next((self.data / 'transfers').iterdir())
            self.assertEqual(self.fixture.command('transfer-cleanup')['removed'], 0)
            old = time.time() - 3700
            os.utime(staged, (old, old))
            self.assertEqual(self.fixture.command('transfer-cleanup')['removed'], 0)
            self.assertTrue(staged.exists())
            process.communicate('exit\n', timeout=10)
            self.assertEqual(process.returncode, 71)
            self.assertEqual(self.fixture.command('transfer-cleanup')['removed'], 1)
            self.assertFalse(staged.exists())
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)

    def test_bundle_older_than_one_hour_cannot_be_consumed(self):
        path = self.launch()
        old = time.time() - 3700
        os.utime(path, (old, old))
        result = self.fixture.command('transfer-read', '--bundle', path, '--provider', 'codex', code=2)
        self.assertNotIn('card', result)

    def test_switch_uses_configured_delta_limits(self):
        directory = self.home / '.claude/projects/delta'
        directory.mkdir(parents=True)
        (directory / 'native-123.jsonl').write_text(''.join(json.dumps({
            'type': 'user', 'cwd': str(self.project), 'timestamp': '2026-11-09T10:00:00Z',
            'message': {'content': 'line-' + str(index)}}) + '\n' for index in range(20)))
        config = self.data / 'config.json'
        value = json.loads(config.read_text())
        value['session_delta'] = {'max_messages': 2, 'max_characters': 30}
        config.write_text(json.dumps(value))
        before = config.read_bytes()
        result = self.switch.preview()
        self.assertEqual(result['manifest']['delta']['included_messages'], 2)
        self.assertLessEqual(result['manifest']['delta']['characters'], 30)
        self.assertEqual(config.read_bytes(), before)

    def test_card_changed_during_consent_never_launches_from_stale_context(self):
        def update_card():
            self.fixture.card('claude', session='new-source', revision=1)
            return 'yes'
        code, output = self.switch.interactive(update_card)
        self.assertEqual(code, 3, output)
        owner = self.fixture.command('card', 'locate', self.project)['metadata']
        self.assertEqual(owner['session_id'], 'new-source')
        self.assertFalse((self.data / 'transfers').exists())
        self.assertFalse((self.home / 'fake-native.json').exists())

    def test_no_noninteractive_consent_bypass_flag(self):
        before = self.fixture.tree()
        result = subprocess.run([sys.executable, str(ROOT / 'bin/deskmate'), 'switch',
                                 '--folder', str(self.project), '--to', 'codex', '--yes'],
                                env=self.fixture.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.fixture.tree(), before)

    def test_incomplete_quoted_credentials_including_truncated_delta_block_transfer(self):
        self.card('password="SYNTHETIC_UNCLOSED_PASSWORD')
        result = self.switch.preview(code=4)
        self.assertEqual(result['reason'], 'uncertain_secret')
        self.assertGreater(result['manifest']['blocked_findings'], 0)
        self.assertNotIn('SYNTHETIC_UNCLOSED_PASSWORD', json.dumps(result))

    def test_character_limited_delta_never_leaks_a_cut_quoted_password(self):
        directory = self.home / '.claude/projects/delta'
        directory.mkdir(parents=True)
        message = 'password="SYNTHETIC_TRUNCATED_PASSWORD"'
        (directory / 'native-123.jsonl').write_text(json.dumps({
            'type': 'user', 'cwd': str(self.project), 'timestamp': '2026-11-09T10:00:00Z',
            'message': {'content': message}}) + '\n')
        config = self.data / 'config.json'
        value = json.loads(config.read_text())
        value['session_delta'] = {'max_messages': 1, 'max_characters': len(message) - 1}
        config.write_text(json.dumps(value))
        result = self.switch.preview(code=4)
        self.assertEqual(result['reason'], 'uncertain_secret')
        self.assertGreater(result['manifest']['blocked_findings'], 0)
        self.assertNotIn('SYNTHETIC_TRUNCATED_PASSWORD', json.dumps(result))

    def test_ambiguous_multiline_credentials_block_preview_and_launch(self):
        variants = ['credentials: { value: MULTILINE_CREDENTIAL_CANARY }',
                    'password: [ MULTILINE_CREDENTIAL_CANARY ]',
                    'password: |\n  MULTILINE_CREDENTIAL_CANARY',
                    'api_token: >-\n  MULTILINE_CREDENTIAL_CANARY',
                    'password = """\nMULTILINE_CREDENTIAL_CANARY\n"""',
                    'password:\n  MULTILINE_CREDENTIAL_CANARY',
                    'password=\\\n  MULTILINE_CREDENTIAL_CANARY']
        for content in variants:
            with self.subTest(content=content.splitlines()[0]):
                candidate = self.home / 'multiline-candidate.md'
                candidate.write_text('# Demo\n## Status\n' + content + '\n## Checks\n')
                revision = self.fixture.command('card', 'locate', self.project)['metadata']['revision']
                self.fixture.command('card', 'write', self.project, '--expected-revision', revision,
                                     '--provider', 'claude', '--session-id', 'native-123', '--from', candidate)
                before = self.fixture.tree()
                result = self.switch.preview(code=4)
                self.assertEqual(result['reason'], 'uncertain_secret')
                self.assertGreater(result['manifest']['blocked_findings'], 0)
                self.assertNotIn('MULTILINE_CREDENTIAL_CANARY', json.dumps(result))
                code, output = self.switch.interactive('yes')
                self.assertEqual(code, 4, output)
                self.assertNotIn('Confirm transfer', output)
                self.assertEqual(self.fixture.tree(), before)
                self.assertFalse((self.data / 'transfers').exists())

    def test_multiline_credentials_in_delta_block_transfer(self):
        directory = self.home / '.claude/projects/multiline'
        directory.mkdir(parents=True)
        (directory / 'native-123.jsonl').write_text(json.dumps({
            'type': 'user', 'cwd': str(self.project), 'timestamp': '2026-11-09T10:00:00Z',
            'message': {'content': 'password: |\n  DELTA_MULTILINE_CREDENTIAL_CANARY'}}) + '\n')
        before = self.fixture.tree()
        result = self.switch.preview(code=4)
        self.assertEqual(result['reason'], 'uncertain_secret')
        self.assertNotIn('DELTA_MULTILINE_CREDENTIAL_CANARY', json.dumps(result))
        self.assertEqual(self.fixture.tree(), before)

    def test_escaped_quoted_passwords_are_fully_redacted(self):
        values = ['password="left\\"SYNTHETIC_DOUBLE_SUFFIX"',
                  "password='left\\'SYNTHETIC_SINGLE_SUFFIX'"]
        self.card('\n'.join(values))
        preview = self.switch.preview()
        self.assertGreaterEqual(preview['manifest']['redactions'].get('credential', 0), 2)
        path = self.launch()
        self.assertNotIn('SYNTHETIC_DOUBLE_SUFFIX', path.read_text())
        self.assertNotIn('SYNTHETIC_SINGLE_SUFFIX', path.read_text())

    def test_prefixed_environment_credentials_are_removed_from_card_checks_and_delta(self):
        candidate = self.home / 'environment-candidate.md'
        candidate.write_text('# Demo\n## Status\nDATABASE_PASSWORD=SYNTHETIC_DATABASE_CANARY\n'
                             '## Checks\n- env: `printf AWS_SECRET_ACCESS_KEY=SYNTHETIC_AWS_CANARY`\n')
        self.fixture.command('card', 'write', self.project, '--expected-revision', 1,
                             '--provider', 'claude', '--session-id', 'native-123', '--from', candidate)
        directory = self.home / '.claude/projects/delta'
        directory.mkdir(parents=True)
        (directory / 'native-123.jsonl').write_text(json.dumps({
            'type': 'user', 'cwd': str(self.project), 'timestamp': '2026-11-09T10:00:00Z',
            'message': {'content': 'OPENAI_API_KEY="SYNTHETIC_DELTA_CANARY"'}}) + '\n')
        preview = self.switch.preview()
        self.assertGreaterEqual(preview['manifest']['redactions'].get('credential', 0), 3)
        path = self.launch()
        for canary in ['SYNTHETIC_DATABASE_CANARY', 'SYNTHETIC_AWS_CANARY', 'SYNTHETIC_DELTA_CANARY']:
            self.assertNotIn(canary, path.read_text())
            self.assertNotIn(canary, (self.data / 'log.csv').read_text())

    def test_relative_checks_run_in_selected_project_instead_of_caller_checkout(self):
        candidate = self.home / 'cwd-candidate.md'
        candidate.write_text('# Demo\n## Status\nContinue\n## Checks\n- folder: `/bin/pwd`\n')
        self.fixture.command('card', 'write', self.project, '--expected-revision', 1,
                             '--provider', 'claude', '--session-id', 'native-123', '--from', candidate)
        path = self.launch()
        body = json.loads(path.read_text())
        self.assertEqual(body['checks'][0]['output'], str(self.project.resolve()))

    def test_later_commands_cleanup_expired_bundles_but_previews_and_dry_runs_do_not(self):
        path = self.launch()
        fresh = path.parent / 'transfer-fresh.json'
        fresh.write_bytes(path.read_bytes())
        fresh.chmod(0o600)
        old = time.time() - 3700
        os.utime(path, (old, old))
        unrelated = path.parent / 'notes.json'
        unrelated.write_text('KEEP')
        linked = path.parent / 'transfer-symlink.json'
        linked.symlink_to(unrelated)
        self.switch.preview(target='claude')
        self.assertTrue(path.exists())
        self.fixture.command('work-session', '--folder', self.project,
                             '--new', '--provider', 'claude', '--dry-run')
        self.assertTrue(path.exists())
        self.fixture.command('card', 'locate', self.project)
        self.assertFalse(path.exists())
        self.assertTrue(fresh.exists())
        self.assertTrue(linked.is_symlink())
        self.assertEqual(unrelated.read_text(), 'KEEP')

    def test_reverse_switch_launch_and_consumption_use_the_claude_target(self):
        self.fixture.card('codex', revision=1)
        self.fixture.simulated_native('claude', native_id='target-claude')
        code, output = self.switch.interactive('yes', target='claude')
        self.assertEqual(code, 0, output)
        path = next((self.data / 'transfers').glob('transfer-*.json'))
        body = self.fixture.command('transfer-read', '--bundle', path, '--provider', 'claude')
        self.assertEqual((body['source_provider'], body['target_provider']), ('codex', 'claude'))
        self.assertFalse(path.exists())



if __name__ == '__main__':
    unittest.main()
