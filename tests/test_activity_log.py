"""Provider activity scenarios through the public CLI and its durable CSV contract."""
import csv
import datetime as dt
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEGACY = ['date', 'time', 'weekday', 'event', 'detail', 'session', 'cwd',
          'turns', 'input_tokens', 'cache_tokens', 'output_tokens']


class ActivityLogTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = pathlib.Path(self.temporary.name)
        self.data = self.home / 'data'
        self.data.mkdir()
        self.log = self.data / 'log.csv'

    def cli(self, *args, payload=None):
        return subprocess.run([sys.executable, str(ROOT / 'bin/deskmate'), *args],
                              env={**os.environ, 'HOME': str(self.home),
                                   'DESKMATE_DATA_DIR': str(self.data),
                                   'CODEX_HOME': str(self.home / '.codex')},
                              input=json.dumps(payload) if payload is not None else None,
                              text=True, capture_output=True, check=False)

    def rows(self):
        return list(csv.DictReader(io.StringIO(self.log.read_text())))

    def legacy(self):
        self.log.write_text('date,time,weekday,event,detail,session,cwd,turns,input_tokens,cache_tokens,output_tokens\n'
                            '2026-10-30,10:02,fri,checkpoint,"a, b",same,/tmp/demo,2,10,20,30\n')
        return self.log.read_bytes()

    def test_event_migrates_history_and_identifies_both_providers(self):
        original = self.legacy()
        result = self.cli('log-event', 'checkpoint', 'next', 'same', '/tmp/demo', '--provider', 'codex')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([(r['provider'], r['session']) for r in self.rows()],
                         [('claude', 'same'), ('codex', 'same')])
        self.assertEqual(self.rows()[0]['detail'], 'a, b')
        self.assertEqual(self.rows()[0]['input_tokens'], '10')
        self.assertEqual({r['schema_version'] for r in self.rows()}, {'1'})
        self.assertEqual((self.data / 'log.csv.bak').read_bytes(), original)

    def test_migration_is_idempotent_and_default_events_are_claude(self):
        original = self.legacy()
        first = self.cli('log-migrate')
        self.assertEqual(first.returncode, 0, first.stderr)
        migrated = self.log.read_bytes()
        second = self.cli('log-migrate')
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.log.read_bytes(), migrated)
        self.assertEqual((self.data / 'log.csv.bak').read_bytes(), original)
        self.assertEqual(len(list(self.data.glob('log.csv.bak*'))), 1)
        result = self.cli('log-event', 'study-later')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r['provider'] for r in self.rows()], ['claude', 'claude'])

    def test_future_schema_stops_all_writers_before_mutation(self):
        self.log.write_text(','.join([*LEGACY, 'schema_version', 'provider']) + '\n'
                            '2026-10-30,10:02,fri,checkpoint,,same,/tmp/demo,,,,,99,claude\n')
        original = self.log.read_bytes()
        for args in [('log-migrate',), ('log-event', 'checkpoint'), ('token-usage',)]:
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('unsupported log schema 99', result.stderr)
                self.assertEqual(self.log.read_bytes(), original)
                self.assertFalse((self.data / 'log.csv.bak').exists())

    def write_claude_skill_session(self):
        for provider in ('claude', 'codex'):
            result = self.cli('log-event', 'checkpoint', '', 'same', '/tmp/demo', '--provider', provider)
            self.assertEqual(result.returncode, 0, result.stderr)
        projects = self.home / '.claude/projects/demo'
        projects.mkdir(parents=True)
        (projects / 'same.jsonl').write_text('\n'.join(json.dumps(r) for r in [
            {'type': 'user', 'timestamp': '2026-10-30T10:00:00Z',
             'message': {'content': '<command-name>/checkpoint</command-name>'}},
            {'type': 'assistant', 'timestamp': '2026-10-30T10:00:01Z',
             'message': {'id': 'answer', 'usage': {'input_tokens': 10,
                         'cache_creation_input_tokens': 2, 'cache_read_input_tokens': 20,
                         'output_tokens': 3}}},
        ]) + '\n')

    def test_token_attribution_preserves_codex_rows_with_same_native_id(self):
        self.write_claude_skill_session()
        result = self.cli('token-usage', '--session', 'same')
        self.assertEqual(result.returncode, 0, result.stderr)
        claude, codex = self.rows()
        self.assertEqual((claude['turns'], claude['input_tokens'], claude['cache_tokens'], claude['output_tokens']),
                         ('1', '12', '20', '3'))
        self.assertEqual((codex['provider'], codex['input_tokens']), ('codex', ''))

    def test_native_hooks_log_skills_without_jq_and_return_native_json(self):
        for provider, prompt in [('claude', '/checkpoint ready'), ('codex', '$checkpoint ready')]:
            with self.subTest(provider=provider):
                result = self.cli('hook-event', '--provider', provider, payload={
                    'hook_event_name': 'UserPromptSubmit', 'session_id': 'same',
                    'cwd': '/tmp/demo', 'prompt': prompt})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual([(r['provider'], r['event'], r['detail']) for r in self.rows()],
                         [('claude', 'checkpoint', 'ready'), ('codex', 'checkpoint', 'ready')])

    def test_metrics_keeps_event_identity_and_usage_separate(self):
        self.legacy()
        result = self.cli('log-event', 'checkpoint', '', 'same', '/tmp/demo', '--provider', 'codex')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli('--json', 'metrics', '--provider', 'all')
        self.assertEqual(result.returncode, 0, result.stderr)
        metrics = json.loads(json.loads(result.stdout)['stdout'])
        claude, codex = metrics['providers']['claude'], metrics['providers']['codex']
        self.assertEqual(claude['events'], {'checkpoint': 1})
        self.assertEqual(codex['events'], {'checkpoint': 1})
        self.assertEqual([(s['provider'], s['id']) for p in (claude, codex) for s in p['sessions']],
                         [('claude', 'same'), ('codex', 'same')])
        self.assertEqual(claude['skill_usage'], {'turns': 2, 'input_tokens': 10,
                                              'cache_tokens': 20, 'output_tokens': 30})
        self.assertIsNone(codex['skill_usage'])
        self.assertNotIn('total_tokens', metrics)

    def test_stop_hook_updates_claude_usage_but_does_not_create_fake_skill_run(self):
        self.write_claude_skill_session()
        rows = self.rows()
        for row in rows:
            for name in ('turns', 'input_tokens', 'cache_tokens', 'output_tokens'):
                row[name] = ''
        with self.log.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        result = self.cli('hook-event', '--provider', 'claude', payload={
            'hook_event_name': 'Stop', 'session_id': 'same', 'cwd': '/tmp/demo'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(len(self.rows()), 2)
        self.assertEqual(self.rows()[0]['input_tokens'], '12')
        self.assertEqual(self.rows()[1]['input_tokens'], '')

    def test_claude_session_statistics_do_not_take_codex_resume_rating(self):
        for provider, rating in [('claude', '1'), ('codex', '3')]:
            self.cli('log-event', 'resume-rating', rating, 'same', '/tmp/demo', '--provider', provider)
        projects = self.home / '.claude/projects/demo'
        projects.mkdir(parents=True)
        today = dt.date.today().isoformat()
        records = [{'type': 'user', 'timestamp': today + 'T12:00:00', 'cwd': '/tmp/demo',
                    'message': {'content': 'work'}}]
        records += [{'type': 'assistant', 'timestamp': today + 'T12:00:01',
                     'message': {'id': str(i), 'usage': {'input_tokens': 100, 'output_tokens': 10}}}
                    for i in range(5)]
        (projects / 'same.jsonl').write_text('\n'.join(json.dumps(r) for r in records) + '\n')
        result = self.cli('session-stats', '--since', today)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('rating 1.0 (1 given)', result.stdout)
        self.assertNotIn('rating 3.0', result.stdout)

    def test_invalid_history_is_not_replaced_or_backed_up(self):
        self.legacy()
        self.log.write_text(self.log.read_text() + 'broken,row\n')
        original = self.log.read_bytes()
        result = self.cli('log-migrate')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(self.log.read_bytes(), original)
        self.assertFalse((self.data / '.log.lock').exists())
        self.assertFalse((self.data / 'log.csv.bak').exists())

    def test_empty_current_log_is_safe_and_future_schema_creates_no_lock(self):
        self.log.write_text(','.join([*LEGACY, 'schema_version', 'provider']) + '\n')
        result = self.cli('log-event', 'checkpoint')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows()[0]['provider'], 'claude')
        (self.data / '.log.lock').unlink()
        self.log.write_text(self.log.read_text().replace(',1,claude', ',99,claude'))
        original = self.log.read_bytes()
        result = self.cli('log-event', 'checkpoint')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.log.read_bytes(), original)
        self.assertFalse((self.data / '.log.lock').exists())

    def test_concurrent_writers_preserve_every_event_and_one_legacy_backup(self):
        original = self.legacy()
        env = {**os.environ, 'HOME': str(self.home), 'DESKMATE_DATA_DIR': str(self.data)}
        processes = [subprocess.Popen([sys.executable, str(ROOT / 'bin/deskmate'),
                                      'log-event', 'checkpoint', str(i), 'same', '/tmp/demo',
                                      '--provider', 'codex'], env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True) for i in range(8)]
        for process in processes:
            _, error = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, error)
        self.assertEqual(len(self.rows()), 9)
        self.assertEqual({r['detail'] for r in self.rows()[1:]}, set(map(str, range(8))))
        self.assertEqual((self.data / 'log.csv.bak').read_bytes(), original)
        self.assertEqual(len(list(self.data.glob('log.csv.bak*'))), 1)

    def test_claude_tool_hook_requires_skill_tool_and_does_not_log_mentions(self):
        for payload in [
            {'hook_event_name': 'UserPromptSubmit', 'prompt': 'mention /checkpoint here'},
            {'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'skill': 'checkpoint'}},
        ]:
            result = self.cli('hook-event', '--provider', 'claude', payload=payload)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists())
        result = self.cli('hook-event', '--provider', 'claude', payload={
            'hook_event_name': 'PreToolUse', 'tool_name': 'Skill', 'session_id': 'same',
            'tool_input': {'skill': 'checkpoint', 'args': 'ready'}})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([(r['event'], r['detail']) for r in self.rows()], [('checkpoint', 'ready')])

    def test_future_raw_usage_schema_stops_hook_before_any_mutation(self):
        directory = self.data / 'usage'
        directory.mkdir()
        usage = directory / 'claude.json'
        original = b'{"schema_version":99,"provider":"claude","sessions":{}}\n'
        usage.write_bytes(original)
        self.legacy()
        log_before = self.log.read_bytes()
        result = self.cli('hook-event', '--provider', 'claude', payload={
            'hook_event_name': 'Stop', 'session_id': 'same'})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('unsupported raw usage schema', result.stderr)
        self.assertEqual(usage.read_bytes(), original)
        self.assertEqual(self.log.read_bytes(), log_before)
        self.assertFalse((self.data / '.log.lock').exists())

    def write_native_usage_sessions(self):
        self.write_claude_skill_session()
        claude_path = self.home / '.claude/projects/demo/same.jsonl'
        codex_path = self.home / '.codex/sessions/2026/10/30/rollout-usage.jsonl'
        codex_path.parent.mkdir(parents=True)
        records = [
            {'type': 'session_meta', 'timestamp': '2026-10-30T10:00:00Z',
             'payload': {'id': 'same', 'cwd': '/tmp/demo', 'timestamp': '2026-10-30T10:00:00Z'}},
            {'type': 'response_item', 'timestamp': '2026-10-30T10:00:01Z',
             'payload': {'type': 'message', 'role': 'user',
                         'content': [{'type': 'input_text', 'text': 'SYNTHETIC_PRIVATE_CONVERSATION'}]}},
            {'type': 'event_msg', 'timestamp': '2026-10-30T10:00:02Z',
             'payload': {'type': 'token_count', 'info': {
                 'total_token_usage': {'input_tokens': 120, 'cached_input_tokens': 40,
                                      'output_tokens': 30, 'reasoning_output_tokens': 20, 'total_tokens': 150},
                 'model_context_window': 100000}}},
        ]
        codex_path.write_text('\n'.join(json.dumps(record) for record in records) + '\n'
                              '{"type":"response_item","payload": INVALID}\n')
        return claude_path, codex_path

    def metrics(self):
        result = self.cli('--json', 'metrics', '--provider', 'all')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertNotIn('SYNTHETIC_PRIVATE_CONVERSATION', result.stdout)
        self.assertNotIn('messages', result.stdout)
        return json.loads(json.loads(result.stdout)['stdout'])['providers']

    def test_metrics_reads_real_native_counters_without_conversation_content(self):
        self.write_native_usage_sessions()
        providers = self.metrics()
        claude, codex = (providers[name]['sessions'][0] for name in ('claude', 'codex'))
        self.assertEqual((claude['provider'], claude['id']), ('claude', 'same'))
        self.assertEqual((codex['provider'], codex['id']), ('codex', 'same'))
        self.assertEqual(claude['usage'], {'turns': 1, 'input_tokens': 10,
                                         'cache_creation_input_tokens': 2,
                                         'cache_read_input_tokens': 20, 'output_tokens': 3})
        self.assertEqual(codex['usage'], {'total_token_usage': {
            'input_tokens': 120, 'cached_input_tokens': 40, 'output_tokens': 30,
            'reasoning_output_tokens': 20, 'total_tokens': 150}, 'model_context_window': 100000})
        self.assertEqual(codex['status'], 'ok')
        self.assertIsNone(providers['codex']['skill_usage'])

    def test_stop_snapshots_are_idempotent_separate_and_cached_when_transcripts_disappear(self):
        paths = self.write_native_usage_sessions()
        contents = [path.read_text() for path in paths]
        snapshots = {}
        for provider in ('claude', 'codex'):
            payload = {'hook_event_name': 'Stop', 'session_id': 'same', 'cwd': '/tmp/demo'}
            first = self.cli('hook-event', '--provider', provider, payload=payload)
            self.assertEqual(first.returncode, 0, first.stderr)
            path = self.data / 'usage' / (provider + '.json')
            before = path.read_bytes()
            second = self.cli('hook-event', '--provider', provider, payload=payload)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(path.read_bytes(), before)
            self.assertNotIn(b'SYNTHETIC_PRIVATE_CONVERSATION', before)
            self.assertNotIn(b'messages', before)
            snapshots[provider] = json.loads(before)['sessions']['same']['usage']
        self.assertEqual(self.rows()[0]['input_tokens'], '12')
        self.assertEqual(self.rows()[1]['input_tokens'], '')
        for path in paths:
            path.unlink()
        for provider, report in self.metrics().items():
            record = report['sessions'][0]
            self.assertEqual(record['status'], 'cached')
            self.assertEqual(record['usage'], snapshots[provider])
        # Reappearing native counters supersede the cache; they are never added
        # to its previous cumulative values.
        for path, content in zip(paths, contents):
            path.write_text(content)
        text = paths[1].read_text().replace('"total_tokens": 150', '"total_tokens": 190')
        paths[1].write_text(text)
        codex = self.metrics()['codex']['sessions'][0]
        self.assertEqual(codex['status'], 'ok')
        self.assertEqual(codex['usage']['total_token_usage']['total_tokens'], 190)
