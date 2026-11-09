"""Session delta acceptance through the stable CLI and synthetic native stores."""
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
SESSION = 'delta-session'


class SessionDeltaTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()
        self.project = self.home / 'project with spaces'
        self.project.mkdir()
        self.data = self.home / 'data'
        self.codex = self.home / '.codex'
        self.env = {**os.environ, 'HOME': str(self.home), 'CODEX_HOME': str(self.codex),
                    'DESKMATE_DATA_DIR': str(self.data), 'TZ': 'UTC'}

    def invoke(self, *args):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'bin/deskmate'),
                                 '--json', *args], env=self.env, capture_output=True,
                                text=True, timeout=15)
        envelope = json.loads(result.stdout)
        self.assertNotIn('Traceback', envelope['stderr'])
        return result.returncode, envelope

    def delta(self, provider='claude', *args):
        code, envelope = self.invoke('session-delta', '--provider', provider,
                                     '--session-id', SESSION, '--format', 'json', *args)
        self.assertEqual(code, 0, envelope)
        return json.loads(envelope['stdout'])

    def config(self, value):
        self.data.mkdir(exist_ok=True)
        path = self.data / 'config.json'
        path.write_text(json.dumps(value))
        return path

    def history(self, kind, messages):
        """Messages are role/text pairs, dated at successive minutes from 10:00."""
        if kind == 'claude':
            path = self.home / '.claude/projects/demo' / (SESSION + '.jsonl')
            path.parent.mkdir(parents=True, exist_ok=True)
            records = [{'type': role, 'cwd': str(self.project),
                        'timestamp': f'2026-11-06T10:{i:02}:00Z',
                        'message': {'content': text}} for i, (role, text) in enumerate(messages)]
        elif kind == 'rollout':
            path = self.codex / 'sessions/rollout-delta.jsonl'
            path.parent.mkdir(parents=True, exist_ok=True)
            records = [{'type': 'session_meta', 'timestamp': '2026-11-06T10:00:00Z',
                        'payload': {'id': SESSION, 'cwd': str(self.project),
                                    'timestamp': '2026-11-06T10:00:00Z'}}]
            records += [{'type': 'response_item', 'timestamp': f'2026-11-06T10:{i:02}:00Z',
                         'payload': {'type': 'message', 'role': role, 'content': [
                             {'type': 'input_text' if role == 'user' else 'output_text',
                              'text': text}]}} for i, (role, text) in enumerate(messages)]
        else:
            self.codex.mkdir(exist_ok=True)
            with closing(sqlite3.connect(self.codex / 'state_5.sqlite')) as db, db:
                db.execute('CREATE TABLE threads (id TEXT, cwd TEXT, created_at INTEGER, '
                           'updated_at INTEGER, rollout_path TEXT, tokens_used INTEGER, history_mode TEXT)')
                db.execute('INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (SESSION, str(self.project), 1793959200, 1793959260, '', 0, 'paginated'))
            path = self.codex / 'thread_history_1.sqlite'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE thread_items (thread_id TEXT, rollout_ordinal INTEGER, '
                           'created_at_ms INTEGER, item_json TEXT, item_type TEXT)')
                for i, (role, text) in enumerate(messages):
                    item = ({'type': 'userMessage', 'content': [{'type': 'text', 'text': text}]}
                            if role == 'user' else {'type': 'agentMessage', 'text': text})
                    db.execute('INSERT INTO thread_items VALUES (?, ?, ?, ?, ?)',
                               (SESSION, i, 1793959200000 + i * 60000,
                                json.dumps(item), item['type']))
            return path
        path.write_text(''.join(json.dumps(row) + '\n' for row in records))
        return path

    def checkpoint(self, provider, stamp='2026-11-06T10:01:00+00:00', session=SESSION):
        source = self.home / 'candidate.md'
        source.write_text(f'# Project\n\n## Status\nCheckpoint {stamp}, session `{session}`, '
                          f'folder `{self.project}`.\n- **State:** active\n\n## Checks\n')
        code, envelope = self.invoke('card', 'write', str(self.project), '--expected-revision', '0',
                                     '--provider', provider, '--session-id', session, '--from', str(source))
        self.assertEqual(code, 0, envelope)

    def test_saved_checkpoint_excludes_earlier_messages_in_every_store(self):
        for kind in ('claude', 'rollout', 'paginated'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                # Each native store gets a separate instance/home.
                case = SessionDeltaTest()
                case.setUp()
                try:
                    provider = 'claude' if kind == 'claude' else 'codex'
                    case.history(kind, [('user', 'already saved'), ('assistant', 'checkpoint saved'),
                                        ('user', 'new request'), ('assistant', 'new progress')])
                    case.checkpoint(provider)
                    result = case.delta(provider)
                    self.assertEqual([m['text'] for m in result['messages']], ['new request', 'new progress'])
                    self.assertEqual(result['included_messages'], 2)
                    self.assertEqual(result['omitted_messages'], 0)
                    self.assertEqual(result['characters'], 23)
                    self.assertEqual(result['coverage']['origin'], 'checkpoint')
                    self.assertEqual(result['coverage']['status'], 'full')
                    self.assertFalse(result['truncated'])
                finally:
                    case.doCleanups()

    def test_cancelled_checkpoint_invocation_does_not_discard_unsaved_work(self):
        self.history('claude', [('user', 'unsaved'), ('user', '/checkpoint'),
                                ('user', 'cancel that'), ('assistant', 'continuing')])
        result = self.delta()
        self.assertEqual([m['text'] for m in result['messages']],
                         ['unsaved', '/checkpoint', 'cancel that', 'continuing'])
        self.assertEqual(result['coverage']['origin'], 'session-start')
        self.assertIsNone(result['checkpoint'])

    def test_checkpoint_from_another_session_does_not_cut_current_context(self):
        self.history('claude', [('user', 'unsaved'), ('assistant', 'progress')])
        self.checkpoint('claude', '2026-11-06T11:00:00Z', session='another-session')
        self.assertEqual(self.delta()['included_messages'], 2)

    def test_checkpoint_from_another_provider_does_not_cut_current_context(self):
        self.history('claude', [('user', 'unsaved'), ('assistant', 'progress')])
        self.checkpoint('codex', '2026-11-06T11:00:00Z')
        self.assertEqual(self.delta()['included_messages'], 2)

    def test_legacy_checkpoint_precision_is_disclosed(self):
        self.history('claude', [('user', 'saved'), ('assistant', 'saved too'), ('user', 'new')])
        self.checkpoint('claude', '2026-11-06 10:01')
        result = self.delta()
        self.assertEqual([m['text'] for m in result['messages']], ['new'])
        self.assertEqual(result['checkpoint']['precision'], 'minute')
        self.assertEqual(result['coverage']['status'], 'partial')
        self.assertTrue(result['warnings'])

    def test_default_message_budget_preserves_first_and_latest(self):
        self.history('claude', [('user', f'm{i:02}') for i in range(20)])
        result = self.delta()
        self.assertEqual([m['text'] for m in result['messages']],
                         ['m00', 'm09', 'm10', 'm11', 'm12', 'm13', 'm14', 'm15', 'm16', 'm17', 'm18', 'm19'])
        self.assertEqual(result['limits'], {'max_messages': 12, 'max_characters': 6000})
        self.assertEqual((result['included_messages'], result['omitted_messages']), (12, 8))
        self.assertEqual((result['characters'], result['omitted_characters']), (36, 24))
        self.assertTrue(result['truncated'])
        self.assertEqual(result['coverage']['status'], 'partial')

    def test_default_character_budget_preserves_early_and_recent_context(self):
        self.history('rollout', [('user', 'A' * 4000), ('assistant', 'B' * 4000)])
        result = self.delta('codex')
        self.assertEqual(result['characters'], 6000)
        self.assertEqual(result['omitted_characters'], 2000)
        self.assertEqual(result['messages'][0]['text'], 'A' * 3000)
        self.assertEqual(result['messages'][-1]['text'], 'B' * 3000)
        self.assertTrue(result['truncated'])

    def test_one_character_and_unicode_budgets_prefer_latest_context(self):
        self.history('claude', [('user', 'early'), ('assistant', 'é🙂finish')])
        result = self.delta('claude', '--max-characters', '1')
        self.assertEqual([m['text'] for m in result['messages']], ['é'])
        self.assertEqual((result['characters'], result['omitted_characters']), (1, 12))
        result = self.delta('claude', '--max-messages', '1', '--max-characters', '2')
        self.assertEqual([m['text'] for m in result['messages']], ['é🙂'])

    def test_config_and_one_off_overrides_never_modify_data(self):
        self.history('claude', [('user', 'first'), ('assistant', 'middle'), ('user', 'last')])
        path = self.config({'schema_version': 1, 'session_delta': {'max_messages': 2, 'max_characters': 8}})
        before = path.read_bytes()
        result = self.delta()
        self.assertEqual(result['limits'], {'max_messages': 2, 'max_characters': 8})
        self.assertEqual([m['text'] for m in result['messages']], ['firs', 'last'])
        result = self.delta('claude', '--max-messages', '3', '--max-characters', '30')
        self.assertEqual([m['text'] for m in result['messages']], ['first', 'middle', 'last'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.data.iterdir()), ['config.json'])

    def test_invalid_limits_and_configuration_fail_without_mutation(self):
        for value in (0, -1, True, '12', None):
            with self.subTest(value=value):
                path = self.config({'session_delta': {'max_messages': value}})
                before = path.read_bytes()
                code, result = self.invoke('session-delta', '--provider', 'claude', '--session-id', SESSION)
                self.assertEqual(code, 2, result)
                self.assertEqual(path.read_bytes(), before)
        self.config({})
        for option, value in (('--max-messages', '0'), ('--max-characters', '-1'), ('--after', 'tomorrow'),
                              ('--after', '2026-11-06T10:01:00')):
            with self.subTest(option=option, value=value):
                code, result = self.invoke('session-delta', '--provider', 'claude', '--session-id', SESSION,
                                            option, value)
                self.assertEqual(code, 2, result)

    def test_explicit_boundary_uses_timezone_and_does_not_require_a_card(self):
        self.history('rollout', [('user', 'saved'), ('assistant', 'saved too'), ('user', 'new')])
        result = self.delta('codex', '--after', '2026-11-06T11:01:00+01:00')
        self.assertEqual([m['text'] for m in result['messages']], ['new'])
        self.assertEqual(result['checkpoint']['source'], 'explicit')

    def test_missing_history_returns_successful_degraded_result(self):
        for provider in ('claude', 'codex'):
            with self.subTest(provider=provider):
                result = self.delta(provider)
                self.assertEqual(result['status'], 'degraded')
                self.assertEqual(result['messages'], [])
                self.assertEqual(result['coverage']['status'], 'unavailable')
                self.assertTrue(result['warnings'])

    def test_corrupt_transcript_preserves_available_messages_with_partial_coverage(self):
        for kind in ('claude', 'rollout'):
            with self.subTest(kind=kind):
                path = self.history(kind, [('user', 'available')])
                with path.open('a') as handle:
                    handle.write('{bad private CANARY\n')
                result = self.delta('claude' if kind == 'claude' else 'codex')
                self.assertEqual(result['status'], 'degraded')
                self.assertEqual(result['messages'][0]['text'], 'available')
                self.assertEqual(result['coverage']['status'], 'partial')
                self.assertNotIn('CANARY', json.dumps(result))

    def test_metadata_tool_results_reasoning_and_skill_instructions_are_excluded(self):
        path = self.history('claude', [('user', 'real request')])
        with path.open('a') as handle:
            for row in [
                {'type': 'user', 'isMeta': True, 'message': {'content': 'CANARY skill'}},
                {'type': 'assistant', 'isSidechain': True, 'message': {'content': 'CANARY sidechain'}},
                {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'CANARY output'}]}},
                {'type': 'assistant', 'message': {'content': [{'type': 'thinking', 'thinking': 'CANARY thought'},
                                                             {'type': 'text', 'text': 'real reply'}]}},
            ]:
                handle.write(json.dumps(row) + '\n')
        result = self.delta()
        self.assertEqual([m['text'] for m in result['messages']], ['real request', 'real reply'])
        self.assertNotIn('CANARY', json.dumps(result))
        path = self.history('rollout', [('user', 'real request')])
        with path.open('a') as handle:
            for row in [
                {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': 'CANARY output'}},
                {'type': 'response_item', 'payload': {'type': 'reasoning', 'text': 'CANARY thought'}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer',
                                                     'content': 'CANARY metadata'}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                                                     'content': '<environment_context>CANARY</environment_context>'}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                                                     'content': '<skill>CANARY instructions</skill>'}},
            ]:
                handle.write(json.dumps(row) + '\n')
        result = self.delta('codex')
        self.assertEqual([m['text'] for m in result['messages']], ['real request'])
        self.assertNotIn('CANARY', json.dumps(result))

    def test_paginated_history_filters_tools_and_reports_corrupt_items(self):
        path = self.history('paginated', [('user', 'real request'), ('assistant', 'real reply')])
        with closing(sqlite3.connect(path)) as db, db:
            for ordinal, kind, content in [
                (2, 'commandExecution', '{"type":"commandExecution","output":"CANARY output"}'),
                (3, 'userMessage', '{"type":"userMessage","content":[{"type":"text","text":"<skill>CANARY</skill>"}]}'),
                (4, 'agentMessage', b'\xff\x81'),
            ]:
                db.execute('INSERT INTO thread_items VALUES (?, ?, ?, ?, ?)',
                           (SESSION, ordinal, 1793959200000, content, kind))
        result = self.delta('codex')
        self.assertEqual([m['text'] for m in result['messages']], ['real request', 'real reply'])
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['coverage']['status'], 'partial')
        self.assertNotIn('CANARY', json.dumps(result))

    def test_unknown_message_time_after_checkpoint_is_not_claimed_as_new_work(self):
        path = self.history('claude', [('user', 'saved'), ('assistant', 'checkpoint saved'), ('user', 'new')])
        self.checkpoint('claude')
        with path.open('a') as handle:
            handle.write(json.dumps({'type': 'user', 'message': {'content': 'unknown time'}}) + '\n')
        result = self.delta()
        self.assertEqual([m['text'] for m in result['messages']], ['new'])
        self.assertEqual(result['coverage']['status'], 'partial')
        self.assertTrue(result['warnings'])

    def test_unreadable_native_history_degrades_without_traceback(self):
        path = self.history('claude', [('user', 'unreadable')])
        path.write_bytes(b'\xff\x81')
        result = self.delta()
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['coverage']['status'], 'unavailable')
        self.assertEqual(result['messages'], [])
        self.assertTrue(result['warnings'])

    def test_mismatched_codex_rollout_does_not_expose_another_session(self):
        path = self.history('rollout', [('user', 'CANARY another session')])
        records = path.read_text().splitlines()
        metadata = json.loads(records[0])
        metadata['payload']['id'] = 'other-session'
        records[0] = json.dumps(metadata)
        path.write_text('\n'.join(records) + '\n')
        with closing(sqlite3.connect(self.codex / 'state_5.sqlite')) as db, db:
            db.execute('CREATE TABLE threads (id TEXT, cwd TEXT, created_at INTEGER, '
                       'updated_at INTEGER, rollout_path TEXT, tokens_used INTEGER, history_mode TEXT)')
            db.execute('INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (SESSION, str(self.project), 1793959200, 1793959260, str(path), 0, 'rollout'))
        result = self.delta('codex')
        self.assertEqual(result['messages'], [])
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['coverage']['status'], 'unavailable')
        self.assertNotIn('CANARY', json.dumps(result))

    def test_streaming_consumers_do_not_build_full_conversation_lists(self):
        self.history('claude', [('user', 'first'), ('assistant', 'last')])
        self.history('rollout', [('user', 'first'), ('assistant', 'last')])
        code = (
            'import json,sys\n'
            'sys.path.insert(0, sys.argv[1])\n'
            'import adapter_claude,adapter_codex\n'
            'for adapter in (adapter_claude,adapter_codex):\n'
            '    counts = [0]\n'
            '    def consume(message,session):\n'
            '        counts[0] += 1\n'
            '    record = adapter.read_session("delta-session", on_message=consume)\n'
            '    print(json.dumps([counts[0],record["messages"]]))\n'
        )
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(ROOT / 'tools')],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([json.loads(line) for line in result.stdout.splitlines()], [[2, []], [2, []]])

    def test_late_claude_folder_metadata_still_resolves_saved_checkpoint(self):
        path = self.history('claude', [('user', 'already saved'), ('assistant', 'saved too'), ('user', 'new work')])
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        del rows[0]['cwd']
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.checkpoint('claude')
        result = self.delta()
        self.assertEqual([m['text'] for m in result['messages']], ['new work'])
        self.assertEqual(result['coverage']['origin'], 'checkpoint')
        self.assertEqual(result['coverage']['status'], 'full')

    def test_escaped_unicode_surrogates_degrade_safely_in_all_stores_and_formats(self):
        for kind in ('claude', 'rollout', 'paginated'):
            case = SessionDeltaTest()
            case.setUp()
            try:
                case.history(kind, [('user', 'available'), ('assistant', 'broken\ud800text')])
                provider = 'claude' if kind == 'claude' else 'codex'
                with self.subTest(kind=kind):
                    result = case.delta(provider)
                    self.assertEqual([m['text'] for m in result['messages']], ['available'])
                    self.assertEqual(result['status'], 'degraded')
                    self.assertEqual(result['coverage']['status'], 'partial')
                    self.assertNotIn('broken', json.dumps(result))
                    text_result = subprocess.run(
                        [sys.executable, '-B', str(ROOT / 'bin/deskmate'), 'session-delta',
                         '--provider', provider, '--session-id', SESSION], env=case.env,
                        capture_output=True, text=True, timeout=15)
                    self.assertEqual(text_result.returncode, 0, text_result.stderr)
                    self.assertIn('degraded', text_result.stdout)
                    self.assertIn('warning:', text_result.stdout)
            finally:
                case.doCleanups()

    def test_naive_native_timestamps_are_utc_even_with_local_checkpoint_timezone(self):
        path = self.history('claude', [('user', 'saved'), ('assistant', 'saved too'), ('user', 'new work')])
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[-1]['timestamp'] = '2026-11-06T10:02:00'
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.checkpoint('claude')
        self.env['TZ'] = 'Europe/Rome'
        result = self.delta()
        self.assertEqual([m['text'] for m in result['messages']], ['new work'])
        self.assertEqual(result['coverage']['status'], 'full')

    def test_invalid_native_timestamps_disclose_partial_coverage_without_checkpoint(self):
        path = self.history('rollout', [('user', 'keep work with unknown time')])
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for stamp in ('invalid', '0001-01-01T00:00:00+01:00'):
            with self.subTest(timestamp=stamp):
                rows[-1]['timestamp'] = stamp
                path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
                result = self.delta('codex')
                self.assertEqual([m['text'] for m in result['messages']], ['keep work with unknown time'])
                self.assertIsNone(result['messages'][0]['timestamp'])
                self.assertEqual(result['status'], 'degraded')
                self.assertEqual(result['coverage']['status'], 'partial')
                self.assertTrue(result['warnings'])

    def test_malformed_conversation_content_is_not_reported_as_complete_empty_delta(self):
        for kind in ('claude', 'rollout', 'paginated'):
            case = SessionDeltaTest()
            case.setUp()
            try:
                path = case.history(kind, [('user', 'saved'), ('assistant', 'saved too'), ('user', 'unsaved')])
                provider = 'claude' if kind == 'claude' else 'codex'
                case.checkpoint(provider)
                if kind == 'paginated':
                    with closing(sqlite3.connect(path)) as db, db:
                        db.execute('UPDATE thread_items SET item_json = ? WHERE rollout_ordinal = 2',
                                   (json.dumps({'type': 'userMessage', 'content': [{'type': 'text', 'text': {'CANARY': 'malformed'}}]}),))
                else:
                    rows = [json.loads(line) for line in path.read_text().splitlines()]
                    message = rows[-1]['message'] if kind == 'claude' else rows[-1]['payload']
                    message['content'] = {'CANARY': 'malformed'}
                    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
                with self.subTest(kind=kind):
                    result = case.delta(provider)
                    self.assertEqual(result['messages'], [])
                    self.assertEqual(result['status'], 'degraded')
                    self.assertIn(result['coverage']['status'], ('partial', 'unavailable'))
                    self.assertTrue(result['warnings'])
                    self.assertNotIn('CANARY', json.dumps(result))
            finally:
                case.doCleanups()

    def test_text_mode_discloses_limits_counts_and_degradation(self):
        self.history('claude', [('user', 'early'), ('assistant', 'recent')])
        code, result = self.invoke('session-delta', '--provider', 'claude', '--session-id', SESSION,
                                    '--max-messages', '1')
        self.assertEqual(code, 0, result)
        self.assertIn('recent', result['stdout'])
        self.assertIn('omitted', result['stdout'])
        self.assertIn('partial', result['stdout'])
        self.assertIn('6000', result['stdout'])


if __name__ == '__main__':
    unittest.main()
