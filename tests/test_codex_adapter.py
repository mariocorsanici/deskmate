"""Codex behavior through the stable command, with synthetic runtime storage."""

import json
import hashlib
from contextlib import closing
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SESSION_ID = "019a1234-0000-7000-8000-000000000001"
STAMP = "2026-10-20T12:00:00Z"


class CodexAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = pathlib.Path(self.temporary.name).resolve()
        self.root = ROOT
        self.codex_home = self.home / ".codex"
        self.env = {**os.environ, "HOME": str(self.home),
                    "CODEX_HOME": str(self.codex_home),
                    "DESKMATE_DATA_DIR": str(self.home / "data")}

    def command(self, *args):
        result = subprocess.run([sys.executable, str(self.root / "bin" / "deskmate"),
                                 "--json", *args], env=self.env, cwd=self.root,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        envelope = json.loads(result.stdout)
        self.assertTrue(envelope["ok"], envelope)
        return json.loads(envelope["stdout"])

    def failed_command(self, *args):
        result = subprocess.run([sys.executable, str(self.root / "bin" / "deskmate"),
                                 "--json", *args], env=self.env, cwd=self.root,
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        envelope = json.loads(result.stdout)
        self.assertFalse(envelope["ok"])
        self.assertNotIn("Traceback", envelope["stderr"])
        return json.loads(envelope["stdout"])

    def text_command(self, *args, input_text=None):
        result = subprocess.run([sys.executable, str(self.root / "bin" / "deskmate"),
                                 "--json", *args], env=self.env, cwd=self.root,
                                capture_output=True, text=True, input=input_text, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        envelope = json.loads(result.stdout)
        self.assertTrue(envelope["ok"], envelope)
        return envelope["stdout"]

    def fake_codex(self, body='echo "codex-cli 0.166.0"'):
        directory = self.home / "fake-bin"
        directory.mkdir(exist_ok=True)
        executable = directory / "codex"
        executable.write_text("#!/bin/sh\n" + body + "\n")
        executable.chmod(0o755)
        self.env["PATH"] = str(directory) + os.pathsep + os.environ["PATH"]
        return str(executable)

    def write_rollout(self, records, name="rollout-2026-10-20-test.jsonl"):
        path = self.codex_home / "sessions" / "2026" / "10" / "20" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(record) for record in records) + "\n")
        import datetime as dt
        stamps = [dt.datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")).timestamp()
                  for record in records if isinstance(record, dict) and record.get("timestamp")]
        if stamps:
            os.utime(path, (max(stamps), max(stamps)))
        return path

    def metadata(self, session_id=SESSION_ID, stamp=STAMP):
        return {"type": "session_meta", "timestamp": stamp,
                "payload": {"id": session_id, "timestamp": stamp, "cwd": "/tmp/demo"}}

    def write_paginated_session(self, items):
        self.codex_home.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.codex_home / "state_5.sqlite")) as db, db:
            db.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT NOT NULL, "
                       "created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, cwd TEXT NOT NULL, "
                       "tokens_used INTEGER NOT NULL, history_mode TEXT NOT NULL, archived INTEGER NOT NULL)")
            db.execute("INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (SESSION_ID, str(self.codex_home / "missing-rollout.jsonl"),
                        1792497600, 1792497660, "/tmp/demo", 450, "paginated", 0))
        with closing(sqlite3.connect(self.codex_home / "thread_history_1.sqlite")) as db, db:
            db.execute("CREATE TABLE thread_items (thread_id TEXT, turn_id TEXT, item_id TEXT, "
                       "rollout_ordinal INTEGER, created_at_ms INTEGER, item_json TEXT, item_type TEXT)")
            for ordinal, item in enumerate(items):
                db.execute("INSERT INTO thread_items VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (SESSION_ID, "turn-1", str(ordinal), ordinal,
                            1792497600000 + ordinal * 1000, json.dumps(item), item.get("type", "")))

    def test_paginated_sqlite_metadata_discovery_does_not_require_a_rollout(self):
        self.write_paginated_session([{"type": "userMessage", "id": "user-1", "content": [
            {"type": "text", "text": "private paginated conversation"}]}])
        records = self.command("sessions", "--provider", "codex", "--format", "json",
                               "--since", "2026-10-01", "--messages", "0")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], SESSION_ID)
        self.assertEqual(records[0]["usage"], {"tokens_used": 450})
        self.assertEqual(records[0]["cwd"], "/tmp/demo")
        self.assertNotIn("private paginated conversation", json.dumps(records))

    def test_paginated_sqlite_conversation_excludes_tool_output_and_preserves_usage(self):
        self.write_paginated_session([
            {"type": "userMessage", "id": "user-1", "content": [
                {"type": "text", "text": "Continue the build"}]},
            {"type": "commandExecution", "id": "tool-1", "aggregatedOutput": "raw command output"},
            {"type": "reasoning", "id": "reasoning-1", "summary": ["internal reasoning"]},
            {"type": "agentMessage", "id": "agent-1", "text": "Build completed", "phase": "final_answer"},
        ])
        session = self.command("session", "--provider", "codex", "--session-id", SESSION_ID)
        self.assertEqual(session["status"], "ok")
        self.assertEqual(session["usage"], {"tokens_used": 450})
        self.assertEqual([(item["role"], item["text"]) for item in session["messages"]],
                         [("user", "Continue the build"), ("assistant", "Build completed")])
        self.assertEqual(session["messages"][0]["timestamp"], "2026-10-20T12:00:00+00:00")

    def test_unreadable_paginated_items_degrade_without_hiding_available_metadata(self):
        self.write_paginated_session([{"type": "userMessage", "content": [{"type": "text", "text": "unreadable"}]}])
        with closing(sqlite3.connect(self.codex_home / "thread_history_1.sqlite")) as db, db:
            db.execute("UPDATE thread_items SET item_json = ?", (b"\xff\x81",))
        result = self.command("session", "--provider", "codex", "--session-id", SESSION_ID)
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["usage"], {"tokens_used": 450})
        self.assertEqual(result["messages"], [])
        self.assertTrue(result["warnings"])

    def test_cold_wal_unavailability_is_explicit_and_native_files_are_preserved(self):
        # Catch an unsafe read-write/immutable fallback or fabricated full coverage.
        for database in ("state_5.sqlite", "thread_history_1.sqlite"):
            with self.subTest(database=database):
                case = CodexAdapterTest()
                case.setUp()
                try:
                    case.write_paginated_session([
                        {"type": "agentMessage", "text": "persisted native progress"}])
                    project = case.home / "project"
                    project.mkdir()
                    with closing(sqlite3.connect(case.codex_home / "state_5.sqlite")) as state, state:
                        state.execute("UPDATE threads SET cwd = ?", (str(project),))
                    path = case.codex_home / database
                    with closing(sqlite3.connect(path)) as writer:
                        self.assertEqual(writer.execute("PRAGMA journal_mode=WAL").fetchone(), ("wal",))
                    self.assertFalse(path.with_name(database + "-wal").exists())
                    self.assertFalse(path.with_name(database + "-shm").exists())
                    before = {p.name: p.read_bytes() for p in case.codex_home.iterdir()}

                    # Probe an independent copy: do not warm the source fixture.
                    # Some SQLite builds support cold WAL, so characterize that
                    # capability independently rather than require their failure.
                    probe = case.home / "cold-probe.sqlite"
                    probe.write_bytes(path.read_bytes())
                    table = "threads" if database == "state_5.sqlite" else "thread_items"
                    try:
                        with closing(sqlite3.connect(probe.as_uri() + "?mode=ro", uri=True)) as reader:
                            reader.execute("SELECT count(*) FROM " + table).fetchone()
                        cold_supported = True
                    except sqlite3.OperationalError as error:
                        self.assertIn("unable to open database file", str(error))
                        cold_supported = False

                    delta = case.command("session-delta", "--provider", "codex", "--session-id", SESSION_ID)
                    if cold_supported:
                        self.assertEqual(delta["status"], "ok")
                        self.assertEqual([m["text"] for m in delta["messages"]], ["persisted native progress"])
                    else:
                        self.assertEqual(delta["status"], "degraded")
                        self.assertEqual(delta["coverage"]["status"], "unavailable")
                        self.assertEqual(delta["messages"], [])
                        self.assertEqual(delta["included_messages"], 0)
                        self.assertTrue(any("Project card and Checks" in warning for warning in delta["warnings"]))
                        self.assertEqual({p.name: p.read_bytes() for p in case.codex_home.iterdir()}, before)
                    self.assertEqual(path.read_bytes(), before[database])

                    # Model native-runtime reopening, not a Deskmate rw fallback.
                    with closing(sqlite3.connect(path)) as native_runtime:
                        native_runtime.execute("SELECT count(*) FROM " + table).fetchone()
                        recovered = case.command("session-delta", "--provider", "codex", "--session-id", SESSION_ID)
                        self.assertEqual(recovered["status"], "ok")
                        self.assertEqual(recovered["warnings"], [])
                        self.assertEqual([m["text"] for m in recovered["messages"]], ["persisted native progress"])
                finally:
                    case.doCleanups()

    def test_live_wal_reads_committed_progress_without_changing_native_files(self):
        # immutable=1 would silently miss these committed, uncheckpointed rows.
        self.write_paginated_session([])
        state = self.codex_home / "state_5.sqlite"
        history = self.codex_home / "thread_history_1.sqlite"
        with closing(sqlite3.connect(state)) as native_state, closing(sqlite3.connect(history)) as native_history:
            native_state.execute("PRAGMA journal_mode=WAL")
            native_history.execute("PRAGMA journal_mode=WAL")
            native_state.execute("UPDATE threads SET tokens_used = 987")
            native_state.commit()
            native_history.execute("INSERT INTO thread_items VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (SESSION_ID, "live-turn", "live-item", 1, 1792497660000,
                                    json.dumps({"type": "agentMessage", "text": "fresh WAL-only progress"}), "agentMessage"))
            native_history.commit()
            self.assertGreater(history.with_name(history.name + "-wal").stat().st_size, 32)
            before_names = {p.name for p in self.codex_home.iterdir()}
            # SQLite may update SHM read marks during a read-only transaction;
            # database pages and committed WAL bytes must remain unchanged.
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in self.codex_home.iterdir() if not p.name.endswith("-shm")}
            result = self.command("session", "--provider", "codex", "--session-id", SESSION_ID)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["usage"], {"tokens_used": 987})
            self.assertEqual([m["text"] for m in result["messages"]], ["fresh WAL-only progress"])
            after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in self.codex_home.iterdir() if not p.name.endswith("-shm")}
            self.assertEqual(after, before)
            self.assertEqual({p.name for p in self.codex_home.iterdir()}, before_names)

    def test_malformed_sqlite_metadata_is_reported_as_degraded_json(self):
        self.write_paginated_session([])
        with closing(sqlite3.connect(self.codex_home / "state_5.sqlite")) as db, db:
            db.execute("UPDATE threads SET cwd = ?, tokens_used = ?", (b"\xff", b"\xff"))
        records = self.command("sessions", "--provider", "codex", "--format", "json",
                               "--since", "2026-10-01", "--messages", "0")
        self.assertEqual(records[0]["status"], "degraded")
        self.assertIsNone(records[0]["cwd"])
        self.assertEqual(records[0]["usage"], {})

    def test_discovery_uses_native_identity_and_keeps_conversation_private(self):
        self.write_rollout([
            self.metadata(),
            {"type": "response_item", "timestamp": STAMP,
             "payload": {"type": "message", "role": "user",
                         "content": [{"type": "input_text", "text": "private conversation"}]}},
            {"type": "event_msg", "timestamp": STAMP,
             "payload": {"type": "token_count", "info": {
                 "total_token_usage": {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}}}},
        ])
        records = self.command("sessions", "--provider", "codex", "--format", "json",
                               "--since", "2026-10-01", "--messages", "0")
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual((record["provider"], record["id"], record["cwd"]),
                         ("codex", SESSION_ID, "/tmp/demo"))
        self.assertEqual(record["usage"], {})
        self.assertNotIn("private conversation", json.dumps(records))
        self.assertFalse(record.get("messages"))

    def test_native_rollout_usage_is_reported_without_decoding_conversation_records(self):
        path = self.write_rollout([self.metadata(),
            {"type": "event_msg", "timestamp": STAMP,
             "payload": {"type": "token_count", "info": {
                 "total_token_usage": {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}}}}])
        # A broken conversation record must not affect metadata-only discovery.
        with path.open("a") as handle:
            handle.write('{"type":"response_item","payload": INVALID}\n')
        records = self.command("sessions", "--provider", "codex", "--format", "json",
                               "--since", "2026-10-01", "--messages", "0")
        self.assertEqual(records[0]["status"], "ok")
        session = self.command("session", "--provider", "codex", "--session-id", SESSION_ID)
        self.assertEqual(session["usage"]["total_token_usage"]["total_tokens"], 150)
        usage = self.command("session", "--provider", "codex", "--session-id", SESSION_ID, "--usage-only")
        self.assertEqual(usage["status"], "ok")
        self.assertEqual(usage["usage"]["total_token_usage"]["total_tokens"], 150)
        self.assertNotIn("messages", usage)

    def test_ordinal_rollout_metadata_and_usage_match_current_native_serialization(self):
        meta = self.metadata()
        self.write_rollout([
            {"timestamp": STAMP, "ordinal": 0, "type": "session_meta", "payload": meta["payload"]},
            {"timestamp": STAMP, "ordinal": 1, "type": "event_msg", "payload": {
                "type": "token_count", "info": {"total_token_usage": {"total_tokens": 99}}}},
        ])
        records = self.command("sessions", "--provider", "codex", "--format", "json",
                               "--since", "2026-10-01", "--messages", "0")
        self.assertEqual(records[0]["id"], SESSION_ID)
        usage = self.command("session", "--provider", "codex", "--session-id", SESSION_ID, "--usage-only")
        self.assertEqual(usage["usage"]["total_token_usage"], {"total_tokens": 99})

    def test_current_native_token_records_keep_latest_cumulative_usage(self):
        # Canonicalized by installed codex-cli 0.166.0 migrate-rollouts.
        records = [json.loads(line) for line in
                   (ROOT / "tests/fixtures/codex-token-usage-record.jsonl").read_text().splitlines()]
        path = self.write_rollout(records)
        with path.open("a") as stream:
            stream.write(json.dumps({"type": "token_usage_record", "timestamp": STAMP,
                "payload": {"thread_id": SESSION_ID, "thread_token_usage": {"total_tokens": -1}}}) + "\n")
            stream.write(json.dumps({"type": "event_msg", "timestamp": STAMP,
                "payload": {"type": "token_count", "info": {
                    "total_token_usage": {"total_tokens": 999}}}}) + "\n")
            stream.write('{"type":"response_item","payload": INVALID_PRIVATE_CONTENT}\n')
        usage = self.command("session", "--provider", "codex", "--session-id", SESSION_ID, "--usage-only")
        self.assertEqual(usage["usage"], {"thread_token_usage": {
            "input_tokens": 200, "cached_input_tokens": 30, "cache_write_input_tokens": 0,
            "output_tokens": 50, "reasoning_output_tokens": 15, "total_tokens": 250}})
        self.assertEqual(usage["status"], "degraded")
        self.assertNotIn("messages", usage)
        self.assertNotIn("PRIVATE_CONTENT", json.dumps(usage))
        metadata = self.command("sessions", "--provider", "codex", "--messages", "0",
                                "--since", "2026-10-01", "--format", "json")
        self.assertEqual(metadata[0]["usage"], {})
        self.assertEqual(metadata[0]["status"], "ok")

    def test_indexed_usage_refreshes_native_token_records_and_stop_snapshot(self):
        records = [json.loads(line) for line in
                   (ROOT / "tests/fixtures/codex-token-usage-record.jsonl").read_text().splitlines()]
        path = self.write_rollout(records)
        with path.open("a") as stream:
            stream.write('{"type":"response_item","payload": PRIVATE_CONVERSATION}\n')
        self.write_paginated_session([])
        with closing(sqlite3.connect(self.codex_home / "state_5.sqlite")) as db, db:
            db.execute("UPDATE threads SET rollout_path = ?, tokens_used = 0", (str(path),))
        usage = self.command("session", "--provider", "codex", "--session-id", SESSION_ID, "--usage-only")
        self.assertEqual(usage["usage"], {"tokens_used": 0, "thread_token_usage": {
            "input_tokens": 200, "cached_input_tokens": 30, "cache_write_input_tokens": 0,
            "output_tokens": 50, "reasoning_output_tokens": 15, "total_tokens": 250}})
        self.assertEqual(usage["status"], "ok")
        self.assertNotIn("messages", usage)
        self.assertNotIn("PRIVATE_CONVERSATION", json.dumps(usage))
        stop = self.text_command("hook-event", "--provider", "codex", input_text=json.dumps({
            "hook_event_name": "Stop", "session_id": SESSION_ID, "cwd": "/tmp/demo"}))
        self.assertEqual(json.loads(stop), {})
        raw = (self.home / "data/usage/codex.json").read_text()
        self.assertEqual(json.loads(raw)["sessions"][SESSION_ID]["usage"], usage["usage"])
        self.assertNotIn("messages", raw)
        self.assertNotIn("PRIVATE_CONVERSATION", raw)

    def test_indexed_session_resumes_when_usage_is_degraded(self):
        executable = self.fake_codex()
        path = self.write_rollout([self.metadata(), {
            "type": "token_usage_record", "timestamp": STAMP, "payload": {
                "thread_id": SESSION_ID, "thread_token_usage": {"total_tokens": -1}}}])
        self.write_paginated_session([])
        with closing(sqlite3.connect(self.codex_home / "state_5.sqlite")) as db, db:
            db.execute("UPDATE threads SET rollout_path = ?, cwd = ?", (str(path), str(self.home)))
        metrics = self.command("metrics", "--provider", "codex")
        session = metrics["providers"]["codex"]["sessions"][0]
        self.assertEqual(session["status"], "degraded")
        self.assertIn("Malformed Codex token usage records were skipped.", session["warnings"])
        resumed = self.command("provider-launch", "--provider", "codex", "--folder", str(self.home),
                               "--session-id", SESSION_ID, "--dry-run")
        self.assertEqual(resumed["status"], "ok")
        self.assertEqual(resumed["argv"], [executable, "resume", "--cd", str(self.home), "--", SESSION_ID])
        unknown = self.failed_command("provider-launch", "--provider", "codex", "--folder", str(self.home),
                                      "--session-id", "unknown-session", "--dry-run")
        self.assertEqual(unknown["status"], "error")
        self.assertEqual(unknown["argv"], [])
        with closing(sqlite3.connect(self.codex_home / "state_5.sqlite")) as db, db:
            db.execute("UPDATE threads SET cwd = ?", (b"invalid-folder",))
        invalid = self.failed_command("provider-launch", "--provider", "codex", "--folder", str(self.home),
                                      "--session-id", SESSION_ID, "--dry-run")
        self.assertEqual(invalid["status"], "error")
        self.assertEqual(invalid["argv"], [])

    def test_launch_plans_use_native_new_and_resume_arguments_without_inventing_identity(self):
        executable = self.fake_codex('exit 99')
        folder = self.home / "project with 'quotes'"
        folder.mkdir()
        prompt = "Continue $checkpoint; $(touch should-not-exist)"
        new = self.command("provider-launch", "--provider", "codex", "--folder", str(folder),
                           "--prompt", prompt, "--dry-run")
        self.assertEqual(new["status"], "ok")
        self.assertEqual(new["mode"], "new")
        self.assertIsNone(new["session_id"])
        self.assertEqual(new["argv"], [executable, "--cd", str(folder), "--", prompt])
        self.write_rollout([self.metadata()])
        resumed = self.command("provider-launch", "--provider", "codex", "--folder", str(folder),
                               "--session-id", SESSION_ID, "--dry-run")
        self.assertEqual(resumed["mode"], "resume")
        self.assertEqual(resumed["session_id"], SESSION_ID)
        self.assertEqual(resumed["argv"], [executable, "resume", "--cd", str(folder), "--", SESSION_ID])

    def test_iterm_launch_keeps_prompt_and_title_as_data(self):
        executable = self.fake_codex()
        pathlib.Path(executable).write_text("#!" + sys.executable + "\n"
            "import json,os,pathlib,sys\n"
            "pathlib.Path(os.environ['HOME'],'launched-argv.json').write_text(json.dumps(sys.argv[1:]))\n")
        osascript = pathlib.Path(executable).with_name("osascript")
        osascript.write_text("#!" + sys.executable + "\n"
            "import json,os,pathlib,subprocess,sys\n"
            "pathlib.Path(os.environ['HOME'],'iterm-input.json').write_text(json.dumps([sys.argv[1:],sys.stdin.read()]))\n"
            "subprocess.run(['/bin/sh','-c',sys.argv[2]],check=True)\n")
        osascript.chmod(0o755)
        folder = self.home / "project 'quoted'"
        folder.mkdir()
        prompt = "Do $checkpoint; $(touch unwanted)"
        title = 'project "; do shell script "touch unwanted"'
        launched = self.command("provider-launch", "--provider", "codex", "--folder", str(folder),
                                "--prompt", prompt, "--title", title)
        self.assertEqual(launched["status"], "launched")
        self.assertIsNone(launched["session_id"])
        self.assertEqual(json.loads((self.home / "launched-argv.json").read_text()),
                         ["--cd", str(folder), "--", prompt])
        arguments, script = json.loads((self.home / "iterm-input.json").read_text())
        self.assertEqual(arguments[-1], title)
        self.assertNotIn(prompt, script)
        self.assertNotIn(title, script)
        self.assertFalse((folder / "unwanted").exists())

    def test_hooks_merge_idempotently_and_install_shared_native_skills(self):
        self.fake_codex('case "$*" in\n  "features list") echo "hooks stable true" ;;\n  *) echo "codex-cli 0.166.0" ;;\nesac')
        self.codex_home.mkdir()
        hooks_path = self.codex_home / "hooks.json"
        unrelated = {"type": "command", "command": "printf unrelated"}
        hooks_path.write_text(json.dumps({"description": "user settings", "hooks": {
            "Stop": [{"matcher": "user-matcher", "hooks": [unrelated]}]}}))
        first = self.command("integration", "--provider", "codex")
        installed = json.loads(hooks_path.read_text())
        second = self.command("integration", "--provider", "codex")
        self.assertEqual(json.loads(hooks_path.read_text()), installed)
        self.assertEqual(first["status"], "ok")
        self.assertEqual(second["status"], "ok")
        self.assertEqual(installed["description"], "user settings")
        self.assertIn({"matcher": "user-matcher", "hooks": [unrelated]}, installed["hooks"]["Stop"])
        self.assertEqual(set(installed["hooks"]), {"SessionStart", "SessionEnd", "UserPromptSubmit", "Stop"})
        for event in ("SessionStart", "SessionEnd", "UserPromptSubmit", "Stop"):
            owned = [handler for group in installed["hooks"][event] for handler in group["hooks"]
                     if "hook-event --provider codex" in handler.get("command", "")]
            self.assertEqual(len(owned), 1)
        self.assertIn("/hooks", " ".join(first["guidance"]))
        self.assertIn("$checkpoint", " ".join(first["guidance"]))
        self.assertIn("--verify", " ".join(first["guidance"]))
        for skill in (self.root / "skills").iterdir():
            if (skill / "SKILL.md").is_file():
                link = self.home / ".agents" / "skills" / skill.name
                self.assertTrue(link.is_symlink())
                self.assertEqual(link.resolve(), skill.resolve())
                self.assertIn("policy:\n  allow_implicit_invocation: false\n",
                              (link / "agents" / "openai.yaml").read_text())
        self.command("integration", "--provider", "codex", "--remove")
        self.assertEqual(json.loads(hooks_path.read_text()), {
            "description": "user settings", "hooks": {"Stop": [{"matcher": "user-matcher", "hooks": [unrelated]}]}})
        self.assertFalse((self.home / ".agents" / "skills" / "checkpoint").exists())

    def test_unsupported_native_hooks_produce_actionable_degradation_without_config_mutation(self):
        self.fake_codex('echo "other-feature stable true"')
        self.codex_home.mkdir()
        config = self.codex_home / "config.toml"
        config.write_text('# user settings\nmodel = "chosen-model"\n')
        result = self.command("integration", "--provider", "codex")
        self.assertEqual(result["status"], "degraded")
        self.assertIn("update Codex CLI", " ".join(result["warnings"]))
        self.assertFalse((self.codex_home / "hooks.json").exists())
        self.assertEqual(config.read_text(), '# user settings\nmodel = "chosen-model"\n')

    def test_synthetic_hook_verification_supports_custom_codex_home_and_isolates_logging(self):
        self.fake_codex('echo "hooks stable true"')
        self.codex_home = self.home / "custom runtime home" / "codex"
        self.env["CODEX_HOME"] = str(self.codex_home)
        result = self.command("integration", "--provider", "codex", "--verify")
        self.assertEqual(result["verification"]["status"], "ok")
        self.assertIn("synthetic", result["verification"]["scope"])
        self.assertIn("manual", result["verification"]["scope"])
        self.assertTrue((self.codex_home / "hooks.json").exists())
        self.assertFalse((self.home / "data" / "log.csv").exists())

    def test_codex_only_command_loop_preserves_checkpoint_ownership_and_native_usage(self):
        executable = self.fake_codex('case "$*" in\n  "features list") echo "hooks stable true" ;;\n  *) echo "codex-cli 0.166.0" ;;\nesac')
        unavailable_claude = pathlib.Path(executable).with_name("claude")
        unavailable_claude.write_text("#!/bin/sh\nexit 1\n")
        unavailable_claude.chmod(0o755)
        configured = self.text_command("configure", "--non-interactive", "--default-provider", "codex")
        self.assertIn("Configured Providers: codex", configured)
        self.assertEqual(self.command("integration", "--provider", "codex", "--verify")["verification"]["status"], "ok")
        project = self.home / "codex-only-project"
        project.mkdir()
        self.assertIsNone(self.command("provider-launch", "--provider", "codex", "--folder", str(project), "--dry-run")["session_id"])
        meta = self.metadata()
        meta["payload"]["cwd"] = str(project)
        path = self.write_rollout([meta,
            {"type": "response_item", "timestamp": STAMP, "payload": {
                "type": "message", "role": "user", "content": [{"type": "input_text", "text": "Build locally"}]}},
            {"type": "response_item", "timestamp": STAMP, "payload": {
                "type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Completed patch"}]}},
            {"type": "event_msg", "timestamp": STAMP, "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}}}},
        ])

        def hook(event, prompt=None):
            payload = {"session_id": SESSION_ID, "cwd": str(project), "hook_event_name": event}
            if prompt is not None:
                payload["prompt"] = prompt
            self.assertEqual(self.text_command("hook-event", "--provider", "codex", input_text=json.dumps(payload)).strip(), "{}")

        hook("SessionStart")
        hook("UserPromptSubmit", "$whats-on-today")
        source = self.home / "checkpoint.md"
        source.write_text("# Codex project\n\n## Status\n- **State:** active\n\n## Checks\n- ready: `printf ready`\n")
        checkpoint = self.command("card", "write", str(project), "--expected-revision", "0",
                                  "--provider", "codex", "--session-id", SESSION_ID, "--from", str(source))
        self.assertEqual(checkpoint["metadata"]["provider"], "codex")
        hook("UserPromptSubmit", "$checkpoint Saved patch")
        self.assertIn("ready: ok", self.text_command("check", "--all"))
        resumed = self.command("provider-launch", "--provider", "codex", "--folder", str(project),
                               "--session-id", SESSION_ID, "--dry-run")
        self.assertEqual(resumed["mode"], "resume")
        delta = self.command("sessions", "--provider", "codex", "--since", "2026-10-01",
                             "--messages", "1", "--cut", "80", "--format", "json")
        self.assertEqual(delta[0]["messages"][0]["text"], "Completed patch")
        human = self.text_command("sessions", "--provider", "codex", "--since", "2026-10-01", "--messages", "0")
        self.assertIn("resume:  deskmate work-session --folder", human)
        hook("UserPromptSubmit", "$how-did-it-go")
        hook("UserPromptSubmit", "$call-it-a-day")
        hook("Stop")
        hook("Stop")
        hook("SessionEnd")
        report = self.command("metrics", "--provider", "all", "--since", "2026-10-01")
        self.assertEqual(report["providers"]["claude"]["events"], {})
        codex = report["providers"]["codex"]
        self.assertEqual(codex["events"], {"whats-on-today": 1, "checkpoint": 1, "how-did-it-go": 1,
                                           "call-it-a-day": 1, "session-start": 1, "session-end": 1})
        self.assertIsNone(codex["skill_usage"])
        self.assertEqual(codex["sessions"][0]["usage"]["total_token_usage"]["total_tokens"], 150)
        path.unlink()  # Synthetic runtime history can disappear after Stop.
        cached = self.command("metrics", "--provider", "codex", "--since", "2026-10-01")
        self.assertEqual(cached["providers"]["codex"]["sessions"][0]["usage"]["total_token_usage"]["total_tokens"], 150)
        latest = self.command("card", "locate", str(project))
        self.assertEqual(latest["metadata"]["session_id"], SESSION_ID)

    def test_hook_parse_failure_and_skill_collision_leave_user_configuration_untouched(self):
        self.fake_codex('echo "hooks stable true"')
        self.codex_home.mkdir()
        hook_path = self.codex_home / "hooks.json"
        hook_path.write_text('{"hooks":{"Stop":"unsupported-shape"}}')
        result = self.failed_command("integration", "--provider", "codex")
        self.assertEqual(result["status"], "error")
        self.assertEqual(hook_path.read_text(), '{"hooks":{"Stop":"unsupported-shape"}}')
        hook_path.write_text('{"hooks": {}}')
        collision = self.home / ".agents" / "skills" / "checkpoint"
        collision.mkdir(parents=True)
        (collision / "SKILL.md").write_text("personal skill")
        result = self.failed_command("integration", "--provider", "codex")
        self.assertEqual(result["status"], "error")
        self.assertIn("not owned by Deskmate", " ".join(result["warnings"]))
        self.assertEqual(hook_path.read_text(), '{"hooks": {}}')
        self.assertEqual((collision / "SKILL.md").read_text(), "personal skill")

    def test_hook_removal_preserves_unrelated_empty_groups_and_handlers(self):
        self.fake_codex('echo "hooks stable true"')
        self.command("integration", "--provider", "codex")
        path = self.codex_home / "hooks.json"
        settings = json.loads(path.read_text())
        settings["hooks"]["Stop"][0]["hooks"].append({"type": "command", "command": "echo keep-me"})
        settings["hooks"]["Interrupt"] = [{"matcher": "", "hooks": []}]
        path.write_text(json.dumps(settings))
        self.command("integration", "--provider", "codex", "--remove")
        self.assertEqual(json.loads(path.read_text())["hooks"], {
            "Stop": [{"hooks": [{"type": "command", "command": "echo keep-me"}]}],
            "Interrupt": [{"matcher": "", "hooks": []}],
        })

    def test_launch_errors_are_structured_and_do_not_start_unknown_sessions(self):
        self.fake_codex('exit 99')
        for arguments in (("--folder", str(self.home / "absent")),
                          ("--folder", str(self.home), "--session-id", "unknown-session"),
                          ("--folder", str(self.home), "--title", "bad\nTitle")):
            result = self.failed_command("provider-launch", "--provider", "codex", *arguments)
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["argv"], [])
            self.assertTrue(result["warnings"])

    def test_session_reads_conversation_and_usage_without_tool_output_or_duplicates(self):
        self.write_rollout([
            self.metadata(),
            {"type": "response_item", "timestamp": STAMP,
             "payload": {"type": "message", "role": "developer", "content": "internal metadata"}},
            {"type": "response_item", "timestamp": STAMP,
             "payload": {"type": "message", "role": "user", "content": [
                 {"type": "input_text", "text": "Check the build"}, {"type": "input_image", "image_url": "image"}]}},
            {"type": "event_msg", "timestamp": STAMP,
             "payload": {"type": "user_message", "message": "Check the build"}},
            {"type": "response_item", "timestamp": STAMP,
             "payload": {"type": "function_call_output", "output": "raw tool output"}},
            {"type": "response_item", "timestamp": STAMP,
             "payload": {"type": "reasoning", "text": "private reasoning"}},
            {"type": "response_item", "timestamp": STAMP,
             "payload": {"type": "message", "role": "assistant", "content": [
                 {"type": "output_text", "text": "The build passed"}]}},
        ])
        session = self.command("session", "--provider", "codex", "--session-id", SESSION_ID)
        self.assertEqual(session["status"], "ok")
        self.assertEqual(session["messages"], [
            {"role": "user", "timestamp": STAMP, "text": "Check the build"},
            {"role": "assistant", "timestamp": STAMP, "text": "The build passed"},
        ])
        bounded = self.command("sessions", "--provider", "codex", "--since", "2026-10-01",
                               "--format", "json", "--messages", "1", "--cut", "9")
        self.assertEqual(bounded[0]["messages"], [
            {"role": "assistant", "timestamp": "2026-10-20T12:00:00+00:00", "text": "The build"}])

    def test_unknown_malformed_and_missing_sessions_degrade_without_losing_valid_progress(self):
        path = self.write_rollout([
            self.metadata(),
            {"type": "future_record", "timestamp": STAMP, "payload": {}},
            {"type": "response_item", "timestamp": STAMP,
             "payload": {"type": "message", "role": "assistant", "content": "Saved progress"}},
        ])
        with path.open("a") as handle:
            handle.write('{"unfinished":\nnull\n{"payload": null}\n')
        session = self.command("session", "--provider", "codex", "--session-id", SESSION_ID)
        self.assertEqual(session["status"], "degraded")
        self.assertEqual(session["messages"][0]["text"], "Saved progress")
        self.assertTrue(session["warnings"])
        missing = self.command("session", "--provider", "codex", "--session-id", "../../elsewhere")
        self.assertEqual(missing["status"], "degraded")
        self.assertEqual(missing["messages"], [])
        self.assertIn("Project card", " ".join(missing["warnings"]))

    def test_discovery_uses_requested_period_and_honors_codex_home(self):
        self.write_rollout([self.metadata("old-session", "2026-09-29T23:59:00Z")], "rollout-old.jsonl")
        self.write_rollout([self.metadata()])
        self.write_rollout([{"type": "session_meta", "timestamp": STAMP,
                             "payload": {"id": ["bad-id"], "cwd": 42}}], "rollout-broken.jsonl")
        self.codex_home = self.home / "separate-codex"
        self.env["CODEX_HOME"] = str(self.codex_home)
        self.write_rollout([self.metadata("configured-home-session")])
        records = self.command("sessions", "--provider", "codex", "--format", "json",
                               "--since", "2026-10-01", "--messages", "0")
        self.assertEqual([record["id"] for record in records], ["configured-home-session"])
        self.env["CODEX_HOME"] = str(self.home / ".codex")
        records = self.command("sessions", "--provider", "codex", "--format", "json",
                               "--since", "2026-10-01", "--messages", "0")
        self.assertEqual(len(records), 2)
        self.assertEqual({r["id"] for r in records if r["status"] == "ok"}, {SESSION_ID})


if __name__ == "__main__":
    unittest.main()
