import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMAND = ROOT / "bin" / "deskmate"


class DeskmateCliTest(unittest.TestCase):
    def run_deskmate(self, *args, home):
        env = os.environ.copy()
        env["HOME"] = str(home)
        return subprocess.run(
            [sys.executable, str(COMMAND), *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_check_runs_a_project_card_with_human_readable_output(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            card = home / "project-card.md"
            card.write_text(
                "# Demo\n\n"
                "## Status\n\n"
                "- **State:** active\n\n"
                "## Checks\n\n"
                "- branch: `printf ready`\n",
                encoding="utf-8",
            )

            result = self.run_deskmate("check", str(card), home=home)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "== Demo  (active)\n"
            "   branch: ok  ready\n",
        )
        self.assertEqual(result.stderr, "")

    def test_json_wraps_command_result_in_a_stable_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            card = home / "project-card.md"
            card.write_text(
                "# Demo\n\n"
                "## Status\n\n"
                "- **State:** active\n\n"
                "## Checks\n\n"
                "- branch: `printf ready`\n",
                encoding="utf-8",
            )

            result = self.run_deskmate("--json", "check", str(card), home=home)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "schema_version": 1,
                "ok": True,
                "command": "check",
                "exit_code": 0,
                "stdout": "== Demo  (active)\n   branch: ok  ready\n",
                "stderr": "",
            },
        )
        self.assertEqual(result.stderr, "")

    def test_json_reports_invalid_command_with_usage_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_deskmate(
                "--json", "not-a-command", home=pathlib.Path(directory)
            )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout,
            json.dumps({
                "schema_version": 1,
                "ok": False,
                "command": "not-a-command",
                "exit_code": 2,
                "stdout": "",
                "stderr": "unknown command: not-a-command\n",
            }, sort_keys=True) + "\n",
        )
        self.assertEqual(result.stderr, "")

    def test_sessions_reads_only_the_isolated_claude_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            projects = home / ".claude" / "projects" / "demo"
            projects.mkdir(parents=True)
            timestamp = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            transcript = projects / "session-123.jsonl"
            transcript.write_text(
                "\n".join([
                    json.dumps({
                        "type": "user",
                        "timestamp": timestamp,
                        "cwd": "/tmp/demo",
                        "message": {"content": "Start the work"},
                    }),
                    json.dumps({
                        "type": "assistant",
                        "timestamp": timestamp,
                        "message": {"content": [{"type": "text", "text": "Ready"}]},
                    }),
                ]) + "\n",
                encoding="utf-8",
            )

            result = self.run_deskmate("sessions", home=home)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SESSION session-123", result.stdout)
        self.assertIn("folder:  /tmp/demo", result.stdout)
        self.assertIn("resume:  cd /tmp/demo && claude --resume session-123", result.stdout)
        self.assertIn("USER: Start the work", result.stdout)
        self.assertIn("CLAUDE: Ready", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_help_lists_the_stable_daily_loop_operations(self):
        expected_commands = {
            "check",
            "sessions",
            "session-stats",
            "reminders",
            "open-session",
            "log-event",
            "token-usage",
        }
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_deskmate("--help", home=pathlib.Path(directory))

        self.assertEqual(result.returncode, 0, result.stderr)
        for command in expected_commands:
            self.assertIn(f"  {command:<16}", result.stdout)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
