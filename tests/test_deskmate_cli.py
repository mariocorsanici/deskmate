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
    def run_deskmate(self, *args, home, extra_env=None, input_text=None):
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
            input=input_text,
            check=False,
        )

    def write_executable(self, directory, name, body):
        path = pathlib.Path(directory) / name
        path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        path.chmod(0o755)
        return path

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
            "configure",
            "providers",
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
            "configure",
            "providers",
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

    def test_providers_reports_claude_only_as_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo '2.1.0 (Claude Code)'")

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Claude Code: included (2.1.0 (Claude Code))\n"
            "Codex CLI: excluded (not found)\n",
        )

    def test_providers_reports_codex_only_as_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "codex", "echo 'codex-cli 0.55.0'")

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Claude Code: excluded (not found)\n"
            "Codex CLI: included (codex-cli 0.55.0)\n",
        )

    def test_providers_reports_both_compatible_in_canonical_order(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")
            self.write_executable(binaries, "codex", "echo 'codex 0.55.0'")

            result = self.run_deskmate(
                "--json", "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "providers")
        self.assertEqual(
            payload["stdout"],
            "Claude Code: included (Claude Code 2.1.0)\n"
            "Codex CLI: included (codex 0.55.0)\n",
        )

    def test_providers_excludes_failing_provider_but_keeps_compatible_one(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo broken >&2; exit 7")
            self.write_executable(binaries, "codex", "echo 'codex 0.55.0'")

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Claude Code: excluded (version probe exited 7: broken)\n"
            "Codex CLI: included (codex 0.55.0)\n",
        )

    def test_providers_excludes_unrecognized_version_output(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'mystery 1.0'")

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Claude Code: excluded (unrecognized version output: mystery 1.0)",
            result.stdout,
        )
        self.assertIn("Codex CLI: excluded (not found)", result.stdout)

    def test_providers_rejects_name_only_output_without_a_version(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'claude is unavailable'")

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Claude Code: excluded (unrecognized version output: claude is unavailable)",
            result.stdout,
        )

    def test_providers_isolates_launch_failure_from_healthy_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            claude = binaries / "claude"
            claude.write_text("#!/missing/deskmate-interpreter\n", encoding="utf-8")
            claude.chmod(0o755)
            self.write_executable(binaries, "codex", "echo 'codex 0.55.0'")

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Claude Code: excluded (version probe could not start:", result.stdout)
        self.assertIn("Codex CLI: included (codex 0.55.0)", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_providers_isolates_non_utf8_output_from_healthy_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "/usr/bin/printf '\\377'")
            self.write_executable(binaries, "codex", "echo 'codex 0.55.0'")

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "Claude Code: excluded (version probe returned non-UTF-8 output)",
            result.stdout,
        )
        self.assertIn("Codex CLI: included (codex 0.55.0)", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_providers_times_out_a_hanging_version_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(
                binaries, "claude", "/bin/sleep 3; echo 'Claude Code 2.1.0'"
            )

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Claude Code: excluded (version probe timed out)", result.stdout
        )

    def test_providers_returns_failure_when_neither_provider_is_present(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()

            result = self.run_deskmate(
                "providers", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stdout,
            "Claude Code: excluded (not found)\n"
            "Codex CLI: excluded (not found)\n",
        )

    def test_configure_selects_the_only_compatible_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")

            result = self.run_deskmate(
                "configure",
                "--non-interactive",
                home=home,
                extra_env={"PATH": str(binaries)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "data" / "config.json").read_text())

        self.assertEqual(
            config,
            {
                "schema_version": 1,
                "providers": {"installed": ["claude"], "default": "claude"},
            },
        )
        self.assertIn("Default provider: Claude Code", result.stdout)

    def test_configure_asks_for_a_default_when_both_are_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")
            self.write_executable(binaries, "codex", "echo 'codex 0.55.0'")

            result = self.run_deskmate(
                "configure",
                home=home,
                extra_env={"PATH": str(binaries)},
                input_text="2\n",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "data" / "config.json").read_text())

        self.assertIn("Choose the Default provider", result.stdout)
        self.assertEqual(config["providers"]["installed"], ["claude", "codex"])
        self.assertEqual(config["providers"]["default"], "codex")

    def test_configure_accepts_an_explicit_default_with_both_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")
            self.write_executable(binaries, "codex", "echo 'codex 0.55.0'")

            result = self.run_deskmate(
                "configure",
                "--non-interactive",
                "--default-provider",
                "claude",
                home=home,
                extra_env={"PATH": str(binaries)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "data" / "config.json").read_text())

        self.assertEqual(config["providers"]["default"], "claude")

    def test_configure_refuses_a_hidden_default_with_both_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")
            self.write_executable(binaries, "codex", "echo 'codex 0.55.0'")

            result = self.run_deskmate(
                "configure",
                "--non-interactive",
                home=home,
                extra_env={"PATH": str(binaries)},
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--default-provider is required", result.stderr)
        self.assertFalse((home / "data" / "config.json").exists())

    def test_configure_refuses_an_unavailable_default_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            config_path = data / "config.json"
            original = '{"name": "Test"}\n'
            config_path.write_text(original, encoding="utf-8")
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")

            result = self.run_deskmate(
                "configure",
                "--default-provider",
                "codex",
                home=home,
                extra_env={"PATH": str(binaries)},
            )
            after = config_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Codex CLI is not compatible", result.stderr)
        self.assertEqual(after, original)

    def test_configure_refuses_when_no_provider_is_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()

            result = self.run_deskmate(
                "configure", home=home, extra_env={"PATH": str(binaries)}
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("No compatible Provider found", result.stderr)
        self.assertFalse((home / "data" / "config.json").exists())

    def test_configure_migrates_legacy_config_and_preserves_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            config_path = data / "config.json"
            config_path.write_text(
                json.dumps({
                    "name": "Test",
                    "language": "it",
                    "reminders": {"morning": "08:30"},
                }),
                encoding="utf-8",
            )
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")

            result = self.run_deskmate(
                "configure", home=home, extra_env={"PATH": str(binaries)}
            )
            config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config["schema_version"], 1)
        self.assertEqual(config["name"], "Test")
        self.assertEqual(config["language"], "it")
        self.assertEqual(config["reminders"], {"morning": "08:30"})
        self.assertEqual(
            config["providers"], {"installed": ["claude"], "default": "claude"}
        )

    def test_configure_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")
            environment = {"PATH": str(binaries)}

            first = self.run_deskmate("configure", home=home, extra_env=environment)
            config_path = home / "data" / "config.json"
            first_bytes = config_path.read_bytes()
            second = self.run_deskmate("configure", home=home, extra_env=environment)
            second_bytes = config_path.read_bytes()

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second_bytes, first_bytes)

    def test_configure_rejects_malformed_config_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            config_path = data / "config.json"
            original = b'{"name": "broken"'
            config_path.write_bytes(original)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")

            result = self.run_deskmate(
                "configure", home=home, extra_env={"PATH": str(binaries)}
            )
            after = config_path.read_bytes()

        self.assertEqual(result.returncode, 2)
        self.assertIn("config.json is not valid JSON", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(after, original)

    def test_configure_rejects_future_schema_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            config_path = data / "config.json"
            original = b'{"schema_version": 99, "name": "Future"}\n'
            config_path.write_bytes(original)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")

            result = self.run_deskmate(
                "configure", home=home, extra_env={"PATH": str(binaries)}
            )
            after = config_path.read_bytes()

        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported config schema 99", result.stderr)
        self.assertEqual(after, original)

    def test_configure_rejects_null_schema_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            config_path = data / "config.json"
            original = b'{"schema_version": null, "name": "Test"}\n'
            config_path.write_bytes(original)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")

            result = self.run_deskmate(
                "configure", home=home, extra_env={"PATH": str(binaries)}
            )
            after = config_path.read_bytes()

        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported config schema None", result.stderr)
        self.assertEqual(after, original)

    def test_configure_rejects_nonstandard_json_constants_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            config_path = data / "config.json"
            original = b'{"name": NaN}\n'
            config_path.write_bytes(original)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")

            result = self.run_deskmate(
                "configure", home=home, extra_env={"PATH": str(binaries)}
            )
            after = config_path.read_bytes()

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid JSON constant NaN", result.stderr)
        self.assertEqual(after, original)

    def test_configure_invalid_interactive_selection_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            data = home / "data"
            data.mkdir()
            config_path = data / "config.json"
            original = b'{"name": "Test"}\n'
            config_path.write_bytes(original)
            binaries = home / "bin"
            binaries.mkdir()
            self.write_executable(binaries, "claude", "echo 'Claude Code 2.1.0'")
            self.write_executable(binaries, "codex", "echo 'codex 0.55.0'")

            result = self.run_deskmate(
                "configure",
                home=home,
                extra_env={"PATH": str(binaries)},
                input_text="neither\n",
            )
            after = config_path.read_bytes()

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid Default provider selection", result.stderr)
        self.assertEqual(after, original)


if __name__ == "__main__":
    unittest.main()
