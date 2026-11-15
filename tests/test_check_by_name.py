"""check.py accepts a project name as well as a card path (ticket L09)."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

CHECK = pathlib.Path(__file__).resolve().parent.parent / "tools" / "check.py"


def card(title, state="active"):
    return f"# {title}\n\n## Status\n- **State:** {state}\n\n## Checks\n"


class CheckByName(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, key, title, state="active"):
        path = self.home / ".claude" / "projects" / key / "memory" / "project-card.md"
        path.parent.mkdir(parents=True)
        path.write_text(card(title, state), encoding="utf-8")
        return path

    def check(self, *args):
        return subprocess.run([sys.executable, "-I", str(CHECK), *args], capture_output=True,
                              text=True, env={"HOME": str(self.home), "PATH": "/usr/bin:/bin"})

    def test_existing_path_runs_that_card(self):
        path = self.add("-Users-me-Dev-vlm-demo-builder", "VLM demo builder")
        r = self.check(str(path))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("== VLM demo builder", r.stdout)

    def test_name_matching_one_folder_key_runs_that_card(self):
        self.add("-Users-me-Dev-vlm-demo-builder", "VLM demo builder")
        self.add("-Users-me-Dev-basler", "Basler cameras")
        r = self.check("vlm")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("== VLM demo builder", r.stdout)
        self.assertNotIn("Basler", r.stdout)

    def test_name_matches_title_case_insensitively(self):
        self.add("-Users-me-Dev-fsm", "Fleet Shipment Manager")
        r = self.check("FLEET")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("== Fleet Shipment Manager", r.stdout)

    def test_several_matches_list_candidates_and_fail_without_traceback(self):
        self.add("-Users-me-Dev-fleet-old", "Fleet (old)")
        self.add("-Users-me-Dev-fleet-new", "Fleet (new)")
        r = self.check("fleet")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("Fleet (old)", r.stderr)
        self.assertIn("Fleet (new)", r.stderr)
        self.assertNotIn("==", r.stdout)

    def test_no_match_fails_without_traceback(self):
        self.add("-Users-me-Dev-basler", "Basler cameras")
        r = self.check("vlm")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("vlm", r.stderr)
        self.assertIn("Basler cameras", r.stderr)

    def test_closed_card_does_not_make_a_name_ambiguous(self):
        self.add("-Users-me-Dev-fleet-old", "Fleet (old)", state="closed")
        self.add("-Users-me-Dev-fleet-new", "Fleet (new)")
        r = self.check("fleet")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("== Fleet (new)", r.stdout)
        self.assertNotIn("Fleet (old)", r.stdout)

    def test_closed_card_still_found_when_it_is_the_only_match(self):
        self.add("-Users-me-Dev-fleet-old", "Fleet (old)", state="closed")
        r = self.check("fleet")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("== Fleet (old)", r.stdout)

    def test_unresolved_name_runs_no_card(self):
        self.add("-Users-me-Dev-vlm-demo-builder", "VLM demo builder")
        r = self.check("vlm", "nothing-like-this")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("==", r.stdout)


if __name__ == "__main__":
    unittest.main()
