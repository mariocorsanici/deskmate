"""The evening reminder no longer asks for a retrospective: /whats-on-today proposes it (L05)."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import reminders  # noqa: E402


class ReminderTexts(unittest.TestCase):
    def test_the_evening_reminder_no_longer_asks_for_a_retrospective(self):
        for language, t in reminders.TEXTS.items():
            text = ' '.join(reminders.lines('evening', t))
            self.assertNotIn('/how-did-it-go', text, language)

    def test_morning_reminder_says_the_brief_may_propose_it(self):
        for language, t in reminders.TEXTS.items():
            self.assertIn('/how-did-it-go', ' '.join(t['morning']), language)


if __name__ == '__main__':
    unittest.main()
