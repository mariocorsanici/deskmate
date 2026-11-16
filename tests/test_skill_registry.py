"""Every skill the hook logs is also measured, and every skill closes its measurement."""
import csv
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import activity_log  # noqa: E402
import hook_event  # noqa: E402

# setup configures Deskmate itself; it is not a measured Daily-loop skill.
UNMEASURED = {'setup'}


def shared_skills():
    return {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')} - UNMEASURED


class SkillRegistry(unittest.TestCase):
    def test_every_logged_skill_is_measured(self):
        self.assertEqual(hook_event.SKILLS, activity_log.SKILLS)
        self.assertEqual(shared_skills(), activity_log.SKILLS)

    def test_every_logged_skill_has_a_completion_step(self):
        for skill in activity_log.SKILLS:
            text = (ROOT / 'skills' / skill / 'SKILL.md').read_text(encoding='utf-8')
            self.assertIn(f'deskmate log-event {skill}-end ""', text, skill)
            self.assertIn('--provider <claude|codex>', text, skill)
            self.assertIn('skill-metrics.md', text, skill)
            self.assertNotIn('~/Dev/mc_dev/deskmate', text, skill)

    def test_every_skill_is_explicit_only_in_codex(self):
        for skill in activity_log.SKILLS:
            policy = ROOT / 'skills' / skill / 'agents' / 'openai.yaml'
            self.assertIn('allow_implicit_invocation: false', policy.read_text(encoding='utf-8'), skill)

    def test_agenda_end_event_gets_a_precise_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, 'DESKMATE_DATA_DIR': tmp, 'PYTHONDONTWRITEBYTECODE': '1'}
            subprocess.run([sys.executable, '-I', str(ROOT / 'bin/deskmate'), 'log-event',
                            'agenda-end', '', 'one', '/p'], env=env, check=True, capture_output=True)
            with (Path(tmp) / 'log.csv').open(newline='') as stream:
                row = list(csv.DictReader(stream))[-1]
            stamp = datetime.fromisoformat(row['detail'].replace('Z', '+00:00'))
            self.assertIsNotNone(stamp.tzinfo)
            self.assertEqual(row['usage_scope'], '')


if __name__ == '__main__':
    unittest.main()
