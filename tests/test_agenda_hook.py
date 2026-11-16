"""Invoke the real native hook handler against a temporary log, never installed user data."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AgendaHook(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.data = self.home / 'data'
        self.env = {'HOME': str(self.home), 'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                    'DESKMATE_DATA_DIR': str(self.data), 'PYTHONDONTWRITEBYTECODE': '1'}

    def invoke(self, payload, provider='claude'):
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'bin/deskmate'), 'hook-event',
                                 '--provider', provider],
                                input=json.dumps(payload), text=True, capture_output=True,
                                env=self.env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.data / 'log.csv'
        if not log.exists():
            return []
        with log.open(newline='') as handle:
            return [row for row in csv.DictReader(handle) if not row['event'].startswith('session-')]

    def test_typed_agenda_command_is_logged_with_arguments_and_session(self):
        rows = self.invoke({'hook_event_name': 'UserPromptSubmit',
                            'prompt': '/agenda nota spese novembre',
                            'session_id': 'fixture-session', 'cwd': '/fixture/project'})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['event'], 'agenda')
        self.assertEqual(rows[0]['detail'], 'nota spese novembre')
        self.assertEqual(rows[0]['session'], 'fixture-session')
        self.assertEqual(rows[0]['cwd'], '/fixture/project')
        self.assertEqual((rows[0]['provider'], rows[0]['usage_scope']), ('claude', 'legacy-window'))

    def test_tool_invoked_agenda_is_logged(self):
        rows = self.invoke({'hook_event_name': 'PreToolUse', 'tool_name': 'Skill',
                            'tool_input': {'skill': 'agenda', 'args': 'fatto report'},
                            'session_id': 'fixture-session', 'cwd': '/fixture/project'})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['event'], 'agenda')
        self.assertEqual(rows[0]['detail'], 'fatto report')

    def test_codex_agenda_command_is_logged_without_a_claude_usage_window(self):
        rows = self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': '$agenda fatto report',
                            'session_id': 'codex-session', 'cwd': '/fixture/project'}, provider='codex')
        self.assertEqual([(r['provider'], r['event'], r['detail'], r['usage_scope']) for r in rows],
                         [('codex', 'agenda', 'fatto report', '')])

    def test_mentioning_agenda_in_a_sentence_is_not_a_run(self):
        self.assertEqual(self.invoke({'hook_event_name': 'UserPromptSubmit',
                                      'prompt': 'Later use /agenda for this',
                                      'session_id': 's', 'cwd': '/p'}), [])

    def test_existing_checkpoint_logging_is_preserved(self):
        rows = self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': '/checkpoint',
                            'session_id': 's', 'cwd': '/p'})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['event'], 'checkpoint')


if __name__ == '__main__':
    unittest.main()
