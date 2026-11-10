"""Synthetic Daily loops through installed hooks and the public command boundary."""
import csv
import datetime as dt
import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest

from tests import test_work_sessions as fixtures
from tests import test_provider_switch as switches

ROOT = Path(__file__).resolve().parents[1]


class DailyLoopTest(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.WorkSessionsTest()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.today = dt.date.today().isoformat()
        self.stamp = self.today + 'T10:00:00Z'

    def history(self, provider, sid='same'):
        self.fx.native(provider, sid)
        if provider == 'claude':
            directory = self.fx.home / '.claude/projects/demo'
            index = directory / 'sessions-index.json'
            record = json.loads(index.read_text())
            record['entries'][0].update(created=self.stamp, modified=self.stamp)
            index.write_text(json.dumps(record))
            path = directory / (sid + '.jsonl')
            rows = [{'type': 'user', 'timestamp': self.stamp, 'cwd': str(self.fx.project),
                     'message': {'content': 'CONVERSATION_CANARY_' + provider}}]
        else:
            path = self.fx.home / '.codex/sessions' / ('rollout-' + sid + '.jsonl')
            rows = [{'type': 'session_meta', 'timestamp': self.stamp,
                     'payload': {'id': sid, 'cwd': str(self.fx.project)}},
                    {'type': 'response_item', 'timestamp': self.stamp,
                     'payload': {'type': 'message', 'role': 'user', 'content': [
                         {'type': 'input_text', 'text': 'CONVERSATION_CANARY_' + provider}]}}]
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def sessions(self, *args):
        return self.fx.command('sessions', '--since', self.today, '--format', 'json', *args)

    def test_default_discovery_is_metadata_only_and_includes_both_provider_identities(self):
        for provider in ('claude', 'codex'):
            self.history(provider)
        result = self.sessions()
        self.assertEqual({(r['provider'], r['id']) for r in result},
                         {('claude', 'same'), ('codex', 'same')})
        self.assertNotIn('CONVERSATION_CANARY', json.dumps(result))
        self.assertTrue(all(not r.get('messages') for r in result))

    def test_explicit_message_inspection_uses_bounded_delta_with_coverage(self):
        self.history('codex')
        result = self.sessions('--provider', 'codex', '--messages', '1', '--cut', '8')[0]
        self.assertEqual(len(result['messages']), 1)
        self.assertLessEqual(len(result['messages'][0]['text']), 8)
        self.assertTrue(result['truncated'])
        self.assertIn('coverage', result)
        self.assertGreater(result['omitted_characters'], 0)

    def test_text_message_inspection_discloses_coverage_and_omissions(self):
        self.history('claude')
        code, envelope = self.fx.cli('sessions', '--provider', 'claude', '--since', self.today,
                                     '--messages', '1', '--cut', '8')
        self.assertEqual(code, 0, envelope)
        self.assertIn('omitted_characters', envelope['stdout'])
        self.assertIn('coverage', envelope['stdout'])

    def test_discovery_does_not_offer_current_card_route_as_another_sessions_resume(self):
        for provider in ('claude', 'codex'):
            self.history(provider)
        self.fx.card('claude', 'same')
        code, envelope = self.fx.cli('sessions', '--since', self.today)
        self.assertEqual(code, 0, envelope)
        claude, codex = envelope['stdout'].split('provider: codex')
        self.assertIn('resume:  deskmate work-session --folder', claude)
        self.assertNotIn('resume:  deskmate work-session', codex)
        self.assertIn('codex:same', codex)
        self.assertIn('Checkpoint', codex)

    def installed_hook(self, provider, payload):
        if provider == 'claude':
            config = json.loads((self.fx.home / '.claude/settings.json').read_text())
            hooks = config['hooks']['UserPromptSubmit'][0]['hooks']
        else:
            config = json.loads((self.fx.home / '.codex/hooks.json').read_text())
            hooks = config['hooks']['UserPromptSubmit'][0]['hooks']
        command = shlex.split(hooks[0]['command'])
        result = subprocess.run([sys.executable, *command], env=self.fx.env,
                                input=json.dumps(payload), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})

    def test_daily_loop_in_each_installation_and_both_defaults(self):
        for installed, default in [(('claude',), 'claude'), (('codex',), 'codex'),
                                   (('claude', 'codex'), 'claude'),
                                   (('claude', 'codex'), 'codex')]:
            with self.subTest(installed=installed, default=default):
                fx = fixtures.WorkSessionsTest()
                fx.setUp()
                try:
                    old = self.fx
                    self.fx = fx
                    for provider in ('claude', 'codex'):
                        if provider not in installed:
                            (fx.binaries / provider).unlink()
                    if 'codex' in installed:
                        fx.executable('codex', "import sys\nprint('hooks experimental true' if sys.argv[1:2] == ['features'] else 'codex-cli 0.166.0')\n")
                    config = fx.data / 'config.json'
                    config.write_text(json.dumps({'language': 'en', 'reminders': {'channels': []}}))
                    code, envelope = fx.cli('setup', '--non-interactive', '--default-provider', default)
                    self.assertEqual(code, 0, envelope)
                    for provider in installed:
                        for name in ('whats-on-today', 'checkpoint', 'study-later', 'how-did-it-go', 'call-it-a-day'):
                            location = '.claude' if provider == 'claude' else '.agents'
                            self.assertEqual((fx.home / location / 'skills' / name).resolve(), ROOT / 'skills' / name)
                    (fx.data / 'handoff.md').write_text('# Handoff ' + self.today + '\nContinue Demo.\n')
                    code, envelope = fx.cli('reminders', 'text', 'morning')
                    self.assertEqual(code, 0, envelope)
                    self.assertIn(('/' if default == 'claude' else '$') + 'whats-on-today', envelope['stdout'])
                    route = fx.route()
                    self.assertEqual((route['provider'], route['mode']), (default, 'new'))
                    fx.hook(route['launch_id'], provider=default, session='same')
                    self.history(default)
                    # Actual installed hook command records each native invocation.
                    for name in ('whats-on-today', 'study-later', 'checkpoint', 'how-did-it-go', 'call-it-a-day'):
                        prefix = '/' if default == 'claude' else '$'
                        self.installed_hook(default, {'hook_event_name': 'UserPromptSubmit', 'session_id': 'same',
                            'cwd': str(fx.project), 'prompt': prefix + name + (' bounded deltas' if name == 'study-later' else '')})
                    source = fx.home / 'checkpoint.md'
                    source.write_text('# Demo\n## Status\nCheckpoint ' + self.today + 'T09:00:00Z, session `same`, '
                                      f'folder `{fx.project}`.\n- **State:** active\n## Checks\n- ready: `printf LIVE_OK`\n')
                    metadata = fx.command('card', 'locate', fx.project)['metadata']
                    fx.command('card', 'write', fx.project, '--expected-revision', metadata['revision'],
                               '--provider', default, '--session-id', 'same', '--from', source)
                    resumed = fx.route('--dry-run')
                    self.assertEqual((resumed['provider'], resumed['mode'], resumed['session_id']), (default, 'resume', 'same'))
                    code, envelope = fx.cli('check')
                    self.assertEqual(code, 0, envelope)
                    self.assertIn('ready: ok  LIVE_OK', envelope['stdout'])
                    initial = fx.command('retrospective', '--since', self.today, '--format', 'json')
                    self.assertEqual(initial['deltas'], [])
                    selected = fx.command('retrospective', '--since', self.today, '--select', default + ':same', '--format', 'json')
                    self.assertEqual(selected['selected'], [default + ':same'])
                    self.assertEqual(selected['deltas'][0]['provider'], default)
                    self.assertNotIn('CONVERSATION_CANARY', json.dumps(self.sessions()))
                    delta = fx.command('session-delta', '--provider', default, '--session-id', 'same')
                    self.assertIn('CONVERSATION_CANARY_' + default, json.dumps(delta))
                    (fx.data / 'lessons.md').write_text('# ' + self.today + '\nKeep checkpoints current.\n')
                    (fx.data / 'handoff.md').write_text('# Handoff ' + self.today + '\nResume: `deskmate work-session --folder "' + str(fx.project) + '"`\nLIVE_OK\n')
                    with (fx.data / 'log.csv').open(newline='') as handle:
                        rows = list(csv.DictReader(handle))
                    self.assertEqual({r['provider'] for r in rows}, {default})
                    self.assertEqual([r['detail'] for r in rows if r['event'] == 'study-later'], ['bounded deltas'])
                    before = {str(p.relative_to(fx.data)): p.read_bytes() for p in fx.data.rglob('*') if p.is_file()}
                    code, envelope = fx.cli('remove', '--non-interactive')
                    self.assertEqual(code, 0, envelope)
                    for name, contents in before.items():
                        self.assertEqual((fx.data / name).read_bytes(), contents, name)
                finally:
                    self.fx = old
                    fx.doCleanups()

    def test_confirmed_switch_and_consumption_in_both_directions(self):
        flow = switches.ProviderSwitchTest()
        flow.setUp()
        self.addCleanup(flow.doCleanups)
        for target in ('codex', 'claude'):
            with self.subTest(target=target):
                flow.fixture.simulated_native(target, native_id='new-' + target)
                code, output = flow.interactive('yes', target)
                self.assertEqual(code, 0, output)
                owner = flow.fixture.command('card', 'locate', flow.project)['metadata']
                self.assertEqual((owner['provider'], owner['session_id']), (target, 'new-' + target))
                bundles = list((flow.data / 'transfers').glob('transfer-*.json'))
                self.assertEqual(len(bundles), 1)
                code, envelope = flow.fixture.cli('transfer-read', '--bundle', bundles[0], '--provider', target)
                self.assertEqual(code, 0, envelope)
                self.assertFalse(bundles[0].exists())
