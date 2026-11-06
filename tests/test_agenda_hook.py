"""Invoke the real hooks against a temporary log, never installed user data."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('jq') and shutil.which('zsh'), 'hooks require jq and zsh')
class AgendaHook(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        for name in ('hook_log.sh', 'log_event.sh'):
            target = self.root / 'tools' / name
            shutil.copyfile(ROOT / 'tools' / name, target)
            target.chmod(0o755)

    def invoke(self, payload):
        result = subprocess.run(['zsh', str(self.root / 'tools' / 'hook_log.sh')],
                                input=json.dumps(payload), text=True, capture_output=True,
                                timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.root / 'data' / 'log.csv'
        if not log.exists():
            return []
        with log.open(newline='') as handle:
            return list(csv.DictReader(handle))

    def test_typed_agenda_command_is_logged_with_arguments_and_session(self):
        rows = self.invoke({'hook_event_name': 'UserPromptSubmit',
                            'prompt': '/agenda nota spese novembre',
                            'session_id': 'fixture-session', 'cwd': '/fixture/project'})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['event'], 'agenda')
        self.assertEqual(rows[0]['detail'], 'nota spese novembre')
        self.assertEqual(rows[0]['session'], 'fixture-session')
        self.assertEqual(rows[0]['cwd'], '/fixture/project')

    def test_tool_invoked_agenda_is_logged(self):
        rows = self.invoke({'hook_event_name': 'PreToolUse',
                            'tool_input': {'skill': 'agenda', 'args': 'fatto report'},
                            'session_id': 'fixture-session'})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['event'], 'agenda')
        self.assertEqual(rows[0]['detail'], 'fatto report')

    def test_mentioning_agenda_in_a_sentence_is_not_a_run(self):
        self.assertEqual(self.invoke({'prompt': 'Later use /agenda for this'}), [])

    def test_existing_checkpoint_logging_is_preserved(self):
        rows = self.invoke({'prompt': '/checkpoint'})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['event'], 'checkpoint')


if __name__ == '__main__':
    unittest.main()
