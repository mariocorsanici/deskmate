import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("checks", ROOT / "tools/check.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class RemoteCheckTests(unittest.TestCase):
    def git(self, *args):
        return subprocess.run(["git", *map(str, args)], check=True,
                              capture_output=True, text=True).stdout.strip()

    def test_fetches_quoted_remote_file_without_changing_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote, writer, reader = (base / name for name in ("remote.git", "writer", "reader with spaces"))
            self.git("init", "--bare", "--initial-branch=trunk", remote)
            self.git("clone", remote, writer)
            self.git("-C", writer, "config", "user.name", "Owner")
            self.git("-C", writer, "config", "user.email", "owner@example.test")
            (writer / "ticket.md").write_text("Status: todo\n")
            self.git("-C", writer, "add", "ticket.md")
            self.git("-C", writer, "commit", "-m", "Start ticket")
            self.git("-C", writer, "push", "origin", "trunk")
            self.git("clone", remote, reader)
            original = self.git("-C", reader, "rev-parse", "HEAD")
            (writer / "ticket.md").write_text("Status: done\n")
            self.git("-C", writer, "commit", "-am", "Complete ticket")
            self.git("-C", writer, "push", "origin", "trunk")
            projects = base / "projects"
            card = projects / "one/memory/project-card.md"
            card.parent.mkdir(parents=True)
            card.write_text("# Example\n## Status\n- **State:** active\n## Checks\n"
                            f"- remote ticket: `git -C '{reader}' show origin/trunk:ticket.md | head -1`\n")
            output = io.StringIO()
            with patch.object(checks, "PROJECTS", projects), patch.object(sys, "argv", ["check.py"]):
                with contextlib.redirect_stdout(output):
                    checks.main()
            self.assertIn(f"fetch {reader}: ok", output.getvalue())
            self.assertIn("remote ticket: ok  Status: done", output.getvalue())
            self.assertEqual((reader / "ticket.md").read_text(), "Status: todo\n")
            self.assertEqual(self.git("-C", reader, "rev-parse", "HEAD"), original)


if __name__ == "__main__":
    unittest.main()
