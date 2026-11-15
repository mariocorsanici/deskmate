"""Every skill the hook logs is also measured, and every skill closes its measurement."""
import csv
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import usage_log  # noqa: E402


def hook_skills():
    text = (ROOT / 'tools' / 'hook_log.sh').read_text(encoding='utf-8')
    return set(re.search(r"skills='\^\((.+?)\)\$'", text).group(1).split('|'))


class SkillRegistry(unittest.TestCase):
    def test_every_logged_skill_is_measured(self):
        self.assertEqual(hook_skills(), usage_log.SKILLS)

    def test_every_logged_skill_has_a_completion_step(self):
        for skill in hook_skills():
            text = (ROOT / 'skills' / skill / 'SKILL.md').read_text(encoding='utf-8')
            self.assertIn(f'log_event.sh {skill}-end ""', text, skill)
            self.assertIn('skill-metrics.md', text, skill)

    def test_agenda_end_event_gets_a_precise_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, 'DESKMATE_DATA_DIR': tmp, 'PYTHONDONTWRITEBYTECODE': '1'}
            subprocess.run(['/bin/zsh', str(ROOT / 'tools/log_event.sh'), 'agenda-end', '', 'one', '/p'],
                           env=env, check=True, capture_output=True)
            with (Path(tmp) / 'log.csv').open(newline='') as stream:
                row = list(csv.DictReader(stream))[-1]
            stamp = datetime.fromisoformat(row['detail'].replace('Z', '+00:00'))
            self.assertIsNotNone(stamp.tzinfo)


if __name__ == '__main__':
    unittest.main()
