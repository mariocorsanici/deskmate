import datetime as dt
import csv
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ClaudeAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = pathlib.Path(self.temporary.name)
        self.projects = self.home / '.claude/projects/demo'
        self.projects.mkdir(parents=True)
        self.timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
        self.env = {**os.environ, 'HOME': str(self.home),
                    'DESKMATE_DATA_DIR': str(self.home / 'data')}

    def run_cli(self, *args, input_text=None):
        result = subprocess.run([sys.executable, str(ROOT / 'bin/deskmate'), '--json', *args],
                                env=self.env, capture_output=True, text=True, input=input_text)
        envelope = json.loads(result.stdout)
        self.assertNotIn('Traceback', envelope['stderr'])
        return result.returncode, envelope

    def record(self, *args):
        code, envelope = self.run_cli(*args)
        self.assertEqual(code, 0, envelope)
        return json.loads(envelope['stdout'])

    def transcript(self, records, session='native-123'):
        path = self.projects / (session + '.jsonl')
        path.write_text('\n'.join(json.dumps(record) for record in records) + '\n')
        return path

    def test_discovery_is_metadata_only_even_when_transcript_is_unreadable(self):
        transcript = self.projects / 'native-123.jsonl'
        transcript.mkdir()  # Opening this as a transcript would fail.
        (self.projects / 'sessions-index.json').write_text(json.dumps({'entries': [{
            'sessionId': 'native-123', 'projectPath': '/tmp/demo',
            'created': self.timestamp, 'modified': self.timestamp,
            'firstPrompt': 'CANARY conversation content must stay unread',
        }]}))
        records = self.record('sessions', '--provider', 'claude', '--since', '2020-01-01',
                              '--messages', '0', '--format', 'json')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], 'native-123')
        self.assertEqual(records[0]['cwd'], '/tmp/demo')
        self.assertEqual(records[0]['provider'], 'claude')
        self.assertNotIn('messages', records[0])
        self.assertNotIn('CANARY', json.dumps(records))

    def test_session_reads_conversation_and_deduplicated_usage_despite_bad_rows(self):
        path = self.transcript([
            {'type': 'user', 'cwd': '/tmp/demo', 'timestamp': self.timestamp,
             'message': {'content': 'Start the work'}},
            {'type': 'assistant', 'timestamp': self.timestamp, 'message': {
                'id': 'message-1', 'usage': {'input_tokens': 10, 'output_tokens': 4,
                                          'cache_read_input_tokens': 3},
                'content': [{'type': 'text', 'text': 'Ready'},
                            {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'CANARY'}}]}},
            {'type': 'assistant', 'timestamp': self.timestamp, 'message': {
                'id': 'message-1', 'usage': {'input_tokens': 10, 'output_tokens': 4}}},
            {'type': 'user', 'isMeta': True, 'message': {'content': 'CANARY metadata'}},
            {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'CANARY'}]}},
            ['malformed'], {'type': 'user', 'message': None},
        ])
        with path.open('a') as handle:
            handle.write('{invalid json\n')
        session = self.record('session', '--provider', 'claude', '--session-id', 'native-123')
        self.assertEqual([message['text'] for message in session['messages']], ['Start the work', 'Ready'])
        self.assertEqual(session['usage']['input_tokens'], 10)
        self.assertEqual(session['usage']['output_tokens'], 4)
        self.assertEqual(session['usage']['cache_read_input_tokens'], 3)
        self.assertEqual(session['status'], 'degraded')
        self.assertTrue(session['warnings'])
        self.assertNotIn('CANARY', json.dumps(session))

    def test_indexless_discovery_uses_lifecycle_metadata_without_reading_conversation(self):
        native = self.projects / 'native-123.jsonl'
        native.write_bytes(b'\xff CANARY private conversation\n')
        code, envelope = self.run_cli('hook-event', '--provider', 'claude', input_text=json.dumps({
            'hook_event_name': 'SessionStart', 'session_id': 'native-123',
            'cwd': str(self.home)}))
        self.assertEqual(code, 0, envelope)
        records = self.record('sessions', '--provider', 'claude', '--since', '2020-01-01',
                              '--messages', '0', '--format', 'json')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], 'native-123')
        self.assertEqual(records[0]['cwd'], str(self.home.resolve()))
        self.assertEqual(records[0]['status'], 'ok')
        self.assertIsNotNone(records[0]['start'])
        self.assertNotIn('messages', records[0])
        self.assertNotIn('CANARY', json.dumps(records))

    def test_indexless_discovery_without_identity_evidence_stays_explicitly_degraded(self):
        self.transcript([{'type': 'user', 'cwd': str(self.home), 'sessionId': 'native-123',
                          'message': {'content': 'CANARY conversation'}}])
        records = self.record('sessions', '--provider', 'claude', '--since', '2020-01-01',
                              '--messages', '0', '--format', 'json')
        self.assertIsNone(records[0]['cwd'])
        self.assertEqual(records[0]['status'], 'degraded')
        self.assertTrue(records[0]['warnings'])
        self.assertNotIn('CANARY', json.dumps(records))

    def test_indexless_discovery_preserves_recent_activity_after_an_older_session_start(self):
        code, envelope = self.run_cli('hook-event', '--provider', 'claude', input_text=json.dumps({
            'hook_event_name': 'SessionStart', 'session_id': 'native-123',
            'cwd': str(self.home)}))
        self.assertEqual(code, 0, envelope)
        log = self.home / 'data/log.csv'
        with log.open(newline='') as handle:
            reader = csv.DictReader(handle)
            fields, rows = reader.fieldnames, list(reader)
        rows[0]['date'], rows[0]['time'] = '2020-01-01', '10:00'
        with log.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        self.transcript([{'type': 'user', 'message': {'content': 'CANARY recent conversation'}}])
        records = self.record('sessions', '--provider', 'claude', '--since', '2026-01-01',
                              '--messages', '0', '--format', 'json')
        self.assertEqual([record['id'] for record in records], ['native-123'])
        self.assertEqual(records[0]['cwd'], str(self.home.resolve()))
        self.assertNotIn('CANARY', json.dumps(records))

    def test_bounded_sessions_and_missing_session_keep_daily_loop_available(self):
        self.transcript([{'type': 'user', 'timestamp': self.timestamp,
                          'message': {'content': text}} for text in ['first', 'second', 'third']])
        records = self.record('sessions', '--provider', 'claude', '--messages', '2', '--cut', '3',
                              '--format', 'json')
        self.assertEqual([item['text'] for item in records[0]['messages']], ['f', 'th'])
        missing = self.record('session', '--provider', 'claude', '--session-id', 'absent')
        self.assertEqual(missing['status'], 'degraded')
        self.assertEqual(missing['messages'], [])

    def test_launch_plans_preserve_arguments_and_resume_native_identity(self):
        prompt = 'Continue "quoted" $(touch CANARY) `touch CANARY`'
        plan = self.record('provider-launch', '--provider', 'claude', '--folder', str(self.home),
                           '--prompt', prompt, '--title', 'Demo', '--dry-run')
        self.assertEqual(plan['argv'], ['claude', '--', prompt])
        self.assertEqual(plan['mode'], 'new')
        self.assertIsNone(plan['session_id'])
        resume = self.record('provider-launch', '--provider', 'claude', '--folder', str(self.home),
                             '--session-id', 'native-123', '--dry-run')
        self.assertEqual(resume['argv'], ['claude', '--resume', 'native-123'])
        self.assertEqual(resume['session_id'], 'native-123')
        self.assertEqual(list(self.home.glob('CANARY')), [])

    def test_native_launch_uses_safe_iterm_command_and_reports_failure(self):
        binaries = self.home / 'bin'
        binaries.mkdir()
        output = self.home / 'captured.json'
        fake = binaries / 'osascript'
        fake.write_text(f'#!{sys.executable}\nimport json, pathlib, sys\n'
                        f'pathlib.Path({str(output)!r}).write_text(json.dumps(sys.argv[1:]))\n'
                        'sys.stdin.read()\n')
        fake.chmod(0o755)
        self.env['PATH'] = str(binaries)
        prompt = 'a; touch CANARY $(touch CANARY)'
        plan = self.record('provider-launch', '--provider', 'claude', '--folder', str(self.home),
                           '--prompt', prompt, '--title', 'Demo')
        command = json.loads(output.read_text())[-1]
        self.assertIn("claude -- 'a; touch CANARY $(touch CANARY)'", command)
        self.assertEqual(plan['status'], 'ok')
        self.assertFalse((self.home / 'CANARY').exists())
        fake.write_text('#!/bin/sh\nexit 7\n')
        code, envelope = self.run_cli('provider-launch', '--provider', 'claude', '--folder', str(self.home))
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(envelope['stdout'])['status'], 'error')

    def test_malformed_index_metadata_degrades_without_stopping_session_listing(self):
        (self.projects / 'sessions-index.json').write_text(json.dumps({'entries': [{
            'sessionId': 'native-123', 'projectPath': {'unexpected': 'object'},
            'created': ['bad timestamp'], 'modified': self.timestamp,
        }]}))
        code, envelope = self.run_cli('sessions', '--provider', 'claude', '--messages', '0')
        self.assertEqual(code, 0, envelope)
        records = self.record('sessions', '--provider', 'claude', '--messages', '0', '--format', 'json')
        self.assertEqual(records[0]['status'], 'degraded')
        self.assertIsNone(records[0]['cwd'])

    def test_integration_preserves_unrelated_hooks_and_installs_shared_slash_skills(self):
        settings = self.home / '.claude/settings.json'
        unrelated = {'type': 'command', 'command': 'echo keep deskmate hook-event'}
        settings.write_text(json.dumps({'theme': 'dark', 'hooks': {'SessionStart': [],
            'SessionEnd': [{'hooks': [], 'matcher': 'untouched'}], 'UserPromptSubmit': [{
            'matcher': '', 'hooks': [unrelated, {'type': 'command',
                                               'command': str(ROOT / 'tools/hook_log.sh')}]}]}}))
        configured = self.record('integration', '--provider', 'claude')
        self.assertEqual(configured['status'], 'ok')
        first = settings.read_bytes()
        self.record('integration', '--provider', 'claude')
        self.assertEqual(settings.read_bytes(), first)
        data = json.loads(first)
        self.assertEqual(data['theme'], 'dark')
        self.assertEqual(len(data['hooks']['SessionStart']), 1)
        self.assertEqual(data['hooks']['SessionEnd'][0], {'hooks': [], 'matcher': 'untouched'})
        self.assertEqual(len(data['hooks']['SessionEnd']), 2)
        self.assertIn(unrelated, data['hooks']['UserPromptSubmit'][0]['hooks'])
        hooks = [hook['command'] for entries in data['hooks'].values()
                 for entry in entries for hook in entry['hooks']]
        self.assertEqual(sum('hook-event --provider claude' in hook for hook in hooks), 5)
        self.assertNotIn(str(ROOT / 'tools/hook_log.sh'), hooks)
        for skill in ['checkpoint', 'whats-on-today', 'how-did-it-go', 'call-it-a-day', 'study-later']:
            installed = self.home / '.claude/skills' / skill
            self.assertTrue(installed.is_symlink())
            self.assertEqual(installed.resolve(), ROOT / 'skills' / skill)
            self.assertTrue((installed / 'SKILL.md').is_file())
        self.record('integration', '--provider', 'claude', '--remove')
        self.assertEqual(json.loads(settings.read_text()), {
            'theme': 'dark', 'hooks': {'SessionEnd': [{'hooks': [], 'matcher': 'untouched'}],
                                     'UserPromptSubmit': [{'matcher': '', 'hooks': [unrelated]}]}})
        self.assertFalse((self.home / '.claude/skills/checkpoint').exists())

    def test_integration_invalid_settings_fails_without_replacing_personal_data(self):
        settings = self.home / '.claude/settings.json'
        original = b'{broken'
        settings.write_bytes(original)
        code, envelope = self.run_cli('integration', '--provider', 'claude')
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(envelope['stdout'])['status'], 'error')
        self.assertEqual(settings.read_bytes(), original)
        self.assertFalse((self.home / '.claude/skills').exists())

    def test_integration_verifies_logging_with_isolated_synthetic_hook(self):
        verified = self.record('integration', '--provider', 'claude', '--verify')
        self.assertEqual(verified['verification']['status'], 'ok')
        self.assertEqual(verified['verification']['provider'], 'claude')
        self.assertEqual(verified['verification']['event'], 'checkpoint')
        self.assertFalse((self.home / 'data/log.csv').exists())

    def test_verification_ignores_unrelated_hook_with_invalid_shell_command(self):
        settings = self.home / '.claude/settings.json'
        unrelated = {'type': 'command', 'command': "'"}
        settings.write_text(json.dumps({'hooks': {'UserPromptSubmit': [
            {'hooks': [unrelated]}]}}))
        verified = self.record('integration', '--provider', 'claude', '--verify')
        self.assertEqual(verified['verification']['status'], 'ok')
        self.assertIn(unrelated, json.loads(settings.read_text())['hooks']['UserPromptSubmit'][0]['hooks'])
        self.assertFalse((self.home / 'data/log.csv').exists())

    def test_usage_only_reports_native_counters_without_conversation(self):
        self.transcript([
            {'type': 'user', 'cwd': '/tmp/demo', 'timestamp': self.timestamp,
             'message': {'content': 'CANARY secret text'}},
            {'type': 'assistant', 'timestamp': self.timestamp, 'message': {
                'id': 'message-1', 'content': 'CANARY assistant text', 'usage': {
                    'input_tokens': 10, 'cache_creation_input_tokens': 7,
                    'cache_read_input_tokens': 3, 'output_tokens': 4}}},
            {'type': 'assistant', 'message': {'id': 'message-1', 'usage': {'output_tokens': 4}}},
            {'type': 'assistant', 'isSidechain': True, 'message': {
                'id': 'subagent', 'usage': {'input_tokens': 999}}},
        ])
        usage = self.record('session', '--provider', 'claude', '--session-id', 'native-123', '--usage-only')
        self.assertEqual(usage['usage'], {'input_tokens': 10, 'cache_creation_input_tokens': 7,
                                         'cache_read_input_tokens': 3, 'output_tokens': 4, 'turns': 1})
        self.assertEqual(usage['cwd'], '/tmp/demo')
        self.assertNotIn('messages', usage)
        self.assertNotIn('CANARY', json.dumps(usage))

    def test_requested_period_uses_index_activity_instead_of_recent_file_copy(self):
        self.transcript([], session='old-session')
        self.transcript([], session='current-session')
        (self.projects / 'sessions-index.json').write_text(json.dumps({'entries': [
            {'sessionId': 'old-session', 'created': '2020-01-01T10:00:00Z',
             'modified': '2020-01-01T11:00:00Z', 'projectPath': '/tmp/old'},
            {'sessionId': 'current-session', 'created': self.timestamp,
             'modified': self.timestamp, 'projectPath': '/tmp/current'},
        ]}))
        records = self.record('sessions', '--provider', 'claude', '--since', '2026-01-01',
                              '--messages', '0', '--format', 'json')
        self.assertEqual([record['id'] for record in records], ['current-session'])

    def test_claude_daily_loop_uses_shared_cards_checks_sessions_and_slash_hooks(self):
        self.record('integration', '--provider', 'claude', '--verify')
        folder = str(self.home.resolve())
        self.transcript([
            {'type': 'user', 'cwd': folder, 'timestamp': self.timestamp,
             'message': {'content': 'Continue the project'}},
            {'type': 'assistant', 'timestamp': self.timestamp,
             'message': {'content': 'Checks pass; next step is documented.'}},
        ])

        def invoke(skill):
            code, envelope = self.run_cli('hook-event', '--provider', 'claude', input_text=json.dumps({
                'hook_event_name': 'UserPromptSubmit', 'session_id': 'native-123',
                'cwd': folder, 'prompt': '/' + skill}))
            self.assertEqual(code, 0, envelope)

        invoke('whats-on-today')
        plan = self.record('provider-launch', '--provider', 'claude', '--folder', folder,
                           '--prompt', 'Continue from the Project card', '--dry-run')
        self.assertEqual(plan['mode'], 'new')
        source = self.home / 'checkpoint.md'
        source.write_text('# Demo\n\n## Status\n- **State:** active\n\n## Checks\n- ready: `printf ready`\n')
        code, envelope = self.run_cli('card', 'write', folder, '--provider', 'claude',
                                     '--session-id', 'native-123', '--expected-revision', '0',
                                     '--from', str(source))
        self.assertEqual(code, 0, envelope)
        invoke('checkpoint')
        card = self.record('card', 'locate', folder)
        self.assertEqual(card['metadata']['provider'], 'claude')
        self.assertEqual(card['metadata']['session_id'], 'native-123')
        code, checks = self.run_cli('check', card['path'])
        self.assertEqual(code, 0, checks)
        self.assertIn('ready: ok  ready', checks['stdout'])
        invoke('how-did-it-go')
        candidates = self.record('sessions', '--provider', 'claude', '--messages', '0', '--format', 'json')
        self.assertEqual([candidate['id'] for candidate in candidates], ['native-123'])
        conversation = self.record('session', '--provider', 'claude', '--session-id', 'native-123')
        self.assertEqual(len(conversation['messages']), 2)
        invoke('call-it-a-day')
        report = self.record('metrics', '--provider', 'claude')
        self.assertEqual(report['providers']['claude']['events'], {
            'whats-on-today': 1, 'checkpoint': 1, 'how-did-it-go': 1, 'call-it-a-day': 1})
        continuation = self.record('provider-launch', '--provider', 'claude', '--folder', folder,
                                   '--session-id', card['metadata']['session_id'], '--dry-run')
        self.assertEqual(continuation['mode'], 'resume')

    def test_resume_refuses_an_option_disguised_as_a_native_session_id(self):
        code, envelope = self.run_cli('provider-launch', '--provider', 'claude', '--folder', str(self.home),
                                      '--session-id=--dangerously-skip-permissions', '--dry-run')
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(envelope['stdout'])['status'], 'error')


if __name__ == '__main__':
    unittest.main()
