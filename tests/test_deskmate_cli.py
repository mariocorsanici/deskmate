import csv
import datetime as dt
import json
import os
import pathlib
import pty
import select
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMAND = ROOT / "bin" / "deskmate"


class DeskmateCliTest(unittest.TestCase):
    def run_deskmate(self, *args, home, extra_env=None):
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["DESKMATE_DATA_DIR"] = str(home / "data")
        env.update(extra_env or {})
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

    def test_json_preserves_a_delegated_failure_status(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_deskmate(
                "--json", "sessions", "--since", "not-a-date",
                home=pathlib.Path(directory),
            )

        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["command"], "sessions")
        self.assertEqual(payload["exit_code"], result.returncode)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["stdout"], "")
        self.assertIn("Invalid isoformat string", payload["stderr"])
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

    def test_reminders_uses_the_isolated_data_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            (data / "config.json").write_text(
                json.dumps({
                    "name": "Test",
                    "language": "en",
                    "reminders": {
                        "morning": "invalid",
                        "evening": "17:00",
                        "days": ["mon"],
                        "channels": ["mac"],
                    },
                }),
                encoding="utf-8",
            )

            result = self.run_deskmate("reminders", "check", home=home)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("morning: 'invalid' is not a HH:MM time", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_each_subcommand_help_is_safe(self):
        commands = (
            "check",
            "sessions",
            "session-stats",
            "reminders",
            "open-session",
            "log-event",
            "token-usage",
        )
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            for command in commands:
                with self.subTest(command=command):
                    result = self.run_deskmate(command, "--help", home=home)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(f"usage: deskmate {command}", result.stdout)
                    self.assertEqual(result.stderr, "")

            self.assertFalse((home / "data" / "log.csv").exists())

    def test_json_help_uses_the_stable_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            top_level = self.run_deskmate("--json", "--help", home=home)
            command = self.run_deskmate("--json", "check", "--help", home=home)

        self.assertEqual(top_level.returncode, 0, top_level.stderr)
        top_payload = json.loads(top_level.stdout)
        self.assertEqual(top_payload["command"], None)
        self.assertEqual(top_payload["exit_code"], 0)
        self.assertTrue(top_payload["ok"])
        self.assertIn("usage: deskmate [--json]", top_payload["stdout"])
        self.assertEqual(top_payload["stderr"], "")

        self.assertEqual(command.returncode, 0, command.stderr)
        command_payload = json.loads(command.stdout)
        self.assertEqual(command_payload["command"], "check")
        self.assertEqual(command_payload["exit_code"], 0)
        self.assertTrue(command_payload["ok"])
        self.assertIn("usage: deskmate check", command_payload["stdout"])
        self.assertEqual(command_payload["stderr"], "")

    def test_human_output_streams_before_a_slow_command_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            card = home / "project-card.md"
            card.write_text(
                "# Demo\n\n"
                "## Status\n\n"
                "- **State:** active\n\n"
                "## Checks\n\n"
                "- fast: `printf ready`\n"
                "- slow: `sleep 2; printf done`\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["DESKMATE_DATA_DIR"] = str(home / "data")
            master, slave = pty.openpty()
            process = subprocess.Popen(
                [sys.executable, str(COMMAND), "check", str(card)],
                cwd=ROOT,
                env=env,
                stdout=slave,
                stderr=slave,
                text=False,
            )
            os.close(slave)
            try:
                early_output = ""
                deadline = time.monotonic() + 0.75
                while "fast: ok  ready" not in early_output:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    readable, _, _ = select.select([master], [], [], remaining)
                    if not readable:
                        break
                    early_output += os.read(master, 4096).decode()
                process.wait(timeout=5)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                os.close(master)

        self.assertIn("fast: ok  ready", early_output)
        self.assertNotIn("slow: ok", early_output)

    def test_session_stats_runs_with_isolated_state(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            (data / "config.json").write_text(
                json.dumps({"experiments": {"fresh_sessions": {
                    "since": dt.date.today().isoformat(),
                    "target_days": 5,
                }}}),
                encoding="utf-8",
            )

            result = self.run_deskmate("session-stats", home=home)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("per mode", result.stdout)
        self.assertIn("resume no days yet (target 5)", result.stdout)
        self.assertIn("new    no days yet (target 5)", result.stdout)

    def test_open_session_supports_a_side_effect_free_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)

            result = self.run_deskmate(
                "open-session",
                "--new",
                "Demo",
                str(home),
                "Continue from the Project card",
                home=home,
                extra_env={"DESKMATE_DRY_RUN": "1"},
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[Demo]", result.stdout)
        self.assertIn("claude", result.stdout)
        self.assertIn("Continue\\ from\\ the\\ Project\\ card", result.stdout)

    def test_log_event_and_token_usage_write_only_isolated_state(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            log_result = self.run_deskmate(
                "log-event",
                "study-later",
                "topic",
                "session-123",
                "/tmp/demo",
                home=home,
            )
            token_result = self.run_deskmate(
                "token-usage",
                "--session",
                "session-123",
                "--projects",
                str(home / "transcripts"),
                home=home,
            )
            with (home / "data" / "log.csv").open(newline="") as log_file:
                rows = list(csv.DictReader(log_file))

        self.assertEqual(log_result.returncode, 0, log_result.stderr)
        self.assertEqual(token_result.returncode, 0, token_result.stderr)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event"], "study-later")
        self.assertEqual(rows[0]["detail"], "topic")
        self.assertEqual(rows[0]["session"], "session-123")
        self.assertEqual(rows[0]["cwd"], "/tmp/demo")


if __name__ == "__main__":
    unittest.main()
