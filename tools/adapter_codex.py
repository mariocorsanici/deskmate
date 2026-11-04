"""Codex CLI's native storage and integration behind the Provider contract.

Rollout JSONL is an unstable runtime format. Unknown records are ignored;
unavailable or malformed sessions degrade without stopping the Daily loop.
"""

from __future__ import annotations

import datetime as dt
from contextlib import closing
import json
import os
import pathlib
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parent.parent
ROLLOUT_KIND = re.compile(
    r'^\s*\{\s*(?:(?:"timestamp"\s*:\s*"(?:\\.|[^"\\])*"|"ordinal"\s*:\s*\d+)\s*,\s*)*'
    r'"type"\s*:\s*"([^"]+)"'
)


def codex_home():
    return pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex"))


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=parsed.tzinfo or dt.timezone.utc).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def record(session_id=None):
    return {"provider": "codex", "id": session_id, "cwd": None, "start": None,
            "end": None, "usage": {}, "status": "ok", "warnings": []}


def degraded(session, warning):
    session["status"] = "degraded"
    if warning not in session["warnings"]:
        session["warnings"].append(warning)
    return session


def rollouts():
    return sorted(codex_home().joinpath("sessions").glob("**/rollout-*.jsonl"))


def epoch_time(value):
    try:
        return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat()
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def metadata_rows(session_id=None):
    """Read only native metadata columns, never previews or conversation items."""
    paths = sorted(codex_home().glob("state_*.sqlite"), reverse=True)
    if not paths:
        return []
    path = paths[0]
    # mode=ro prevents creating a missing database or changing its contents.
    # Do not use immutable=1 here: it would ignore live WAL records.
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
        db.row_factory = sqlite3.Row
        columns = {row[1] for row in db.execute("PRAGMA table_info(threads)")}
        required = {"id", "cwd", "created_at", "updated_at", "rollout_path", "tokens_used"}
        if not required <= columns:
            raise ValueError("Unsupported Codex session metadata schema.")
        selected = sorted(required | ({"history_mode"} & columns))
        query = "SELECT " + ",".join(selected) + " FROM threads"
        if session_id is not None:
            query += " WHERE id = ?"
        return [dict(row) for row in db.execute(query, () if session_id is None else (session_id,))]


def indexed_record(row):
    session = record(row["id"] if isinstance(row["id"], str) else None)
    session.update(cwd=row["cwd"] if isinstance(row["cwd"], str) else None,
                   start=epoch_time(row["created_at"]), end=epoch_time(row["updated_at"]))
    if type(row["tokens_used"]) is int and row["tokens_used"] >= 0:
        session["usage"] = {"tokens_used": row["tokens_used"]}
    else:
        degraded(session, "Codex native usage metadata is malformed.")
    if not session["id"] or not session["cwd"] or not session["start"] or not session["end"]:
        degraded(session, "Codex session metadata is missing or unsupported.")
    return session


def read_rollout(path, include_messages=False, usage_only=False):
    session = record()
    if include_messages:
        session["messages"] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not include_messages:
                    match = ROLLOUT_KIND.match(line)
                    allowed = ("session_meta", "event_msg", "token_usage_record") if usage_only else ("session_meta",)
                    if match is None or match[1] not in allowed:
                        continue
                try:
                    entry = json.loads(line)
                    if not isinstance(entry, dict) or not isinstance(entry.get("payload"), dict):
                        raise ValueError("invalid rollout record")
                except (ValueError, TypeError):
                    degraded(session, "Malformed Codex rollout records were skipped.")
                    continue
                payload = entry["payload"]
                stamp = entry.get("timestamp")
                if timestamp(stamp) is not None:
                    session["end"] = stamp
                if entry.get("type") == "session_meta":
                    session["id"] = payload.get("id") if isinstance(payload.get("id"), str) else None
                    session["cwd"] = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
                    session["start"] = payload.get("timestamp", stamp)
                    if not include_messages and not usage_only:
                        session["end"] = epoch_time(path.stat().st_mtime)
                        break
                elif entry.get("type") == "token_usage_record":
                    # Native TokenUsageRecord.thread_token_usage is cumulative:
                    # https://github.com/openai/codex/blob/main/codex-rs/protocol/src/protocol.rs
                    counters = payload.get("thread_token_usage")
                    keys = ("input_tokens", "cached_input_tokens", "output_tokens",
                            "reasoning_output_tokens", "total_tokens")
                    if (payload.get("thread_id") == session["id"] and isinstance(counters, dict)
                            and all(type(counters.get(key)) is int and counters[key] >= 0 for key in keys)
                            and type(counters.get("cache_write_input_tokens", 0)) is int
                            and counters.get("cache_write_input_tokens", 0) >= 0):
                        session["usage"] = {"thread_token_usage": {
                            key: counters.get(key, 0) for key in (*keys, "cache_write_input_tokens")}}
                    else:
                        degraded(session, "Malformed Codex token usage records were skipped.")
                elif entry.get("type") == "event_msg" and payload.get("type") == "token_count":
                    info = payload.get("info")
                    if isinstance(info, dict) and "thread_token_usage" not in session["usage"]:
                        session["usage"] = {key: value for key, value in info.items()
                                            if key in ("total_token_usage", "last_token_usage", "model_context_window")}
                elif include_messages and entry.get("type") == "response_item":
                    if payload.get("type") != "message" or payload.get("role") not in ("user", "assistant"):
                        continue
                    content = payload.get("content")
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = "\n".join(part["text"] for part in content
                                         if isinstance(part, dict)
                                         and part.get("type") in ("input_text", "output_text")
                                         and isinstance(part.get("text"), str))
                    else:
                        continue
                    if text.strip():
                        session["messages"].append({"role": payload["role"], "timestamp": stamp,
                                                    "text": text.strip()})
    except (OSError, UnicodeError):
        degraded(session, "Codex rollout is unavailable or unreadable.")
    if not session["id"] or not session["cwd"] or timestamp(session["start"]) is None:
        degraded(session, "Codex session metadata is missing or unsupported.")
    return session


def discover(since: str) -> list[dict]:
    threshold = dt.datetime.combine(dt.date.fromisoformat(since), dt.time()).timestamp()
    records = []
    try:
        rows = metadata_rows()
    except (sqlite3.Error, OSError, ValueError):
        rows = []
        records.append(degraded(record(), "Codex metadata database is unavailable or unsupported; rollout fallback is in use."))
    indexed_ids = {row["id"] for row in rows}
    for row in rows:
        session = indexed_record(row)
        end = timestamp(session["end"])
        if end is None or end >= threshold:
            records.append(session)
    for path in rollouts():
        session = read_rollout(path)
        if session["id"] in indexed_ids:
            continue
        end = timestamp(session["end"])
        if end is None:
            try:
                end = path.stat().st_mtime
            except OSError:
                continue
        if end >= threshold:
            records.append(session)
    return sorted(records, key=lambda item: item["end"] or "")


def read_session(session_id: str) -> dict:
    if isinstance(session_id, str) and session_id and "/" not in session_id and "\\" not in session_id:
        try:
            rows = metadata_rows(session_id)
        except (sqlite3.Error, OSError, ValueError):
            rows = []
        if rows:
            row = rows[0]
            session = indexed_record(row)
            session["messages"] = []
            if row.get("history_mode") == "paginated":
                return read_paginated(session)
            if not isinstance(row["rollout_path"], str):
                return degraded(session, "Codex rollout metadata is malformed; continue from the Project card and Checks.")
            path = pathlib.Path(row["rollout_path"])
            if path.is_file():
                rollout = read_rollout(path, include_messages=True)
                if rollout["id"] == session_id:
                    rollout["usage"] = {**session["usage"], **rollout["usage"]}
                    return rollout
            return degraded(session, "Codex rollout is unavailable; continue from the Project card and Checks.")
        for path in rollouts():
            session = read_rollout(path)
            if session["id"] == session_id:
                return read_rollout(path, include_messages=True)
    session = degraded(record(session_id), "Codex Work session is unavailable; continue from the Project card and Checks.")
    session["messages"] = []
    return session


def read_usage(session_id: str) -> dict:
    """Refresh native counters without decoding any conversation records."""
    if not isinstance(session_id, str) or not session_id or "/" in session_id or "\\" in session_id:
        return degraded(record(session_id), "Codex Work session is unavailable.")
    try:
        rows = metadata_rows(session_id)
    except (sqlite3.Error, OSError, ValueError):
        rows = []
    if rows:
        row = rows[0]
        session = indexed_record(row)
        if isinstance(row["rollout_path"], str) and pathlib.Path(row["rollout_path"]).is_file():
            rollout = read_rollout(pathlib.Path(row["rollout_path"]), usage_only=True)
            if rollout["id"] == session_id:
                session["usage"].update(rollout["usage"])
                for warning in rollout["warnings"]:
                    degraded(session, warning)
            else:
                degraded(session, "Codex rollout identity does not match indexed Work session.")
        return session
    for path in rollouts():
        session = read_rollout(path)
        if session["id"] == session_id:
            return read_rollout(path, usage_only=True)
    return degraded(record(session_id), "Codex usage is unavailable; continue from the Project card and Checks.")


def read_paginated(session):
    paths = sorted(codex_home().glob("thread_history_*.sqlite"), reverse=True)
    if not paths:
        return degraded(session, "Codex paginated history is unavailable; continue from the Project card and Checks.")
    try:
        with closing(sqlite3.connect(paths[0].resolve().as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
            # Filter before reading item_json, so tool output and reasoning never
            # enter the Session delta reader.
            query = ("SELECT created_at_ms,item_json FROM thread_items WHERE thread_id = ? "
                     "AND item_type IN ('userMessage','agentMessage','user_message','agent_message') "
                     "ORDER BY rollout_ordinal")
            for created_at_ms, item_json in db.execute(query, (session["id"],)):
                try:
                    item = json.loads(item_json)
                    if not isinstance(item, dict):
                        raise ValueError("invalid history item")
                    kind = item.get("type")
                    if kind in ("userMessage", "user_message"):
                        role = "user"
                        content = item.get("content", [])
                        if not isinstance(content, list):
                            raise ValueError("invalid message content")
                        text = "\n".join(part["text"] for part in content if isinstance(part, dict)
                                         and part.get("type") in ("text", "input_text")
                                         and isinstance(part.get("text"), str))
                    elif kind in ("agentMessage", "agent_message"):
                        role = "assistant"
                        text = item.get("text")
                    else:
                        raise ValueError("unsupported conversation item")
                    stamp = epoch_time(created_at_ms / 1000)
                    if not isinstance(text, str) or stamp is None:
                        raise ValueError("invalid conversation item")
                    if text.strip():
                        session["messages"].append({"role": role, "timestamp": stamp, "text": text.strip()})
                except (ValueError, TypeError):
                    degraded(session, "Malformed or unsupported Codex history items were skipped.")
    except (sqlite3.Error, OSError):
        degraded(session, "Codex paginated history is unavailable or unsupported; continue from the Project card and Checks.")
    return session


def resume_available(session_id, folder: str | None = None):
    """Native identity and folder metadata determine resume, independently of analytics."""
    if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", session_id):
        return False
    try:
        rows = metadata_rows(session_id)
    except (sqlite3.Error, OSError, ValueError):
        rows = []
    if rows:
        metadata = rows[0]
        return (metadata["id"] == session_id and isinstance(metadata["cwd"], str)
                and bool(metadata["cwd"].strip())
                and (folder is None or (pathlib.Path(metadata["cwd"]).is_absolute()
                     and pathlib.Path(metadata["cwd"]).resolve() == pathlib.Path(folder).resolve())))
    for path in rollouts():
        metadata = read_rollout(path)
        if metadata["id"] == session_id:
            return (isinstance(metadata["cwd"], str) and bool(metadata["cwd"].strip())
                    and (folder is None or (pathlib.Path(metadata["cwd"]).is_absolute()
                         and pathlib.Path(metadata["cwd"]).resolve() == pathlib.Path(folder).resolve())))
    return False


def launch(folder: str, session_id: str | None = None, prompt: str | None = None,
           dry_run: bool = False, title: str | None = None,
           launch_id: str | None = None) -> dict:
    result = {"provider": "codex", "mode": "resume" if session_id else "new", "argv": [],
              "cwd": str(pathlib.Path(folder).expanduser().resolve()),
              "session_id": session_id, "status": "ok", "warnings": []}
    executable = shutil.which("codex")
    if not pathlib.Path(result["cwd"]).is_dir():
        result.update(status="error", warnings=["Project folder does not exist."])
        return result
    if executable is None:
        result.update(status="error", warnings=["Codex CLI is unavailable; install it or choose another Provider explicitly."])
        return result
    if title and any(ord(char) < 32 or ord(char) == 127 for char in title):
        result.update(status="error", warnings=["Work session title must not contain control characters."])
        return result
    if session_id and not resume_available(session_id):
        result.update(status="error", warnings=["Codex-owned Work session is unavailable; choose a new Work session explicitly."])
        return result
    argv = [executable, *(["resume"] if session_id else []), "--cd", result["cwd"]]
    if session_id or prompt is not None:
        argv.append("--")
    if session_id:
        argv.append(session_id)
    if prompt is not None:
        argv.append(prompt)
    result["argv"] = argv
    context = []
    if launch_id is not None:
        if not re.fullmatch(r'[a-f0-9]{32}', launch_id):
            raise ValueError('Invalid Deskmate launch identity')
        context = ['/usr/bin/env', 'DESKMATE_LAUNCH_ID=' + launch_id,
                   'DESKMATE_DATA_DIR=' + str(pathlib.Path(os.environ.get(
                       'DESKMATE_DATA_DIR', ROOT / 'data')).expanduser().resolve())]
        if 'CODEX_HOME' in os.environ:
            context.append('CODEX_HOME=' + str(pathlib.Path(os.environ['CODEX_HOME']).expanduser().resolve()))
    if dry_run:
        return result
    command = "cd -- " + shlex.quote(result["cwd"]) + " && exec " + shlex.join([*context, *argv])
    script = '''on run argv
    set launchCommand to item 1 of argv
    set tabTitle to item 2 of argv
    tell application "iTerm"
        if (count of windows) is 0 then create window with default profile
        tell current window
            create tab with default profile
            tell current session
                set name to tabTitle
                write text launchCommand
            end tell
        end tell
        activate
    end tell
end run
'''
    try:
        completed = subprocess.run(["osascript", "-", command, title or pathlib.Path(result["cwd"]).name],
                                   input=script, capture_output=True, text=True, timeout=10, check=False)
        if completed.returncode:
            result.update(status="error", warnings=["iTerm launch failed; check iTerm installation and terminal Automation permission."])
        else:
            result["status"] = "launched"
    except (OSError, subprocess.TimeoutExpired):
        result.update(status="error", warnings=["iTerm launch could not be verified; check the terminal before retrying."])
    return result


def hook_capability():
    executable = shutil.which("codex")
    if executable is None:
        return False, "Codex CLI is unavailable; install a release with native hooks and rerun integration."
    try:
        result = subprocess.run([executable, "features", "list"], capture_output=True,
                                text=True, timeout=2, check=False)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                fields = line.split()
                if fields and fields[0] in ("hooks", "codex_hooks"):
                    if fields[-1] == "true":
                        return True, None
                    return False, "Codex hooks are disabled; review features.hooks in Codex configuration or managed policy, enable them, then rerun integration."
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        pass
    return False, "Native Codex hooks could not be verified; update Codex CLI to a release with hooks support and rerun integration."


def hook_argv():
    return [str(ROOT / "bin" / "deskmate"), "hook-event", "--provider", "codex"]


def hooks_path():
    return codex_home() / "hooks.json"


def owns_hook(hook):
    if not isinstance(hook, dict) or hook.get("type") != "command":
        return False
    try:
        return shlex.split(hook.get("command", "")) == hook_argv()
    except (TypeError, ValueError):
        return False


def verification_hook(session_id, cwd):
    """Resolve the installed native prompt hook and its verification payload."""
    settings = json.loads(hooks_path().read_text(encoding="utf-8"))
    for group in settings.get("hooks", {}).get("UserPromptSubmit", []):
        if any(owns_hook(hook) for hook in group.get("hooks", [])):
            return hook_argv(), {"hook_event_name": "UserPromptSubmit",
                                 "session_id": session_id, "cwd": cwd,
                                 "prompt": "$checkpoint integration verification"}
    raise ValueError("Deskmate UserPromptSubmit hook is not installed.")


def configure_hooks(remove: bool = False) -> dict:
    result = {"provider": "codex", "status": "ok", "warnings": [], "guidance": [
        "In Codex CLI, open /hooks and review and trust each Deskmate hook. New or changed definitions are skipped until trusted.",
        "Review normal project trust and command approvals when Codex requests them. Deskmate does not bypass approval or hook trust.",
        "Use native skills such as $checkpoint. User skills are linked under ~/.agents/skills; restart Codex if they are not visible.",
        "Run deskmate integration --provider codex --verify to test synthetic logging. After trusting hooks, run $checkpoint in a real Work session and check its Codex log row to verify runtime delivery.",
    ]}
    path = hooks_path()
    command = shlex.join(hook_argv())
    try:
        settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(settings, dict) or not isinstance(settings.get("hooks", {}), dict):
            raise ValueError("Codex hooks.json must contain a hooks object.")
        hooks = settings.setdefault("hooks", {})
        for groups in hooks.values():
            if not isinstance(groups, list):
                raise ValueError("Codex hook events must contain matcher groups.")
            for group in groups:
                if not isinstance(group, dict) or not isinstance(group.get("hooks"), list) or any(not isinstance(handler, dict) for handler in group["hooks"]):
                    raise ValueError("Codex hook matcher groups must contain hook handlers.")
        skills = [(skill, pathlib.Path.home() / ".agents" / "skills" / skill.name)
                  for skill in sorted((ROOT / "skills").iterdir()) if (skill / "SKILL.md").is_file()]
        # Preflight all collisions before changing either hooks or skill links.
        if not remove:
            for skill, link in skills:
                if (link.exists() or link.is_symlink()) and not (link.is_symlink() and link.resolve() == skill.resolve()):
                    raise ValueError(f"Existing Codex skill is not owned by Deskmate: {link.name}; move or rename it and rerun integration.")
        supported, warning = (True, None) if remove else hook_capability()
        if not supported:
            result.update(status="degraded", warnings=[warning])
        else:
            for event in list(hooks):
                cleaned = []
                for group in hooks[event]:
                    kept = [handler for handler in group["hooks"]
                            if not owns_hook(handler)]
                    if kept or not group["hooks"]:
                        cleaned.append({**group, "hooks": kept})
                if cleaned:
                    hooks[event] = cleaned
                else:
                    del hooks[event]
            if not remove:
                for event in ("SessionStart", "SessionEnd", "UserPromptSubmit", "Stop"):
                    hooks.setdefault(event, []).append({"hooks": [{"type": "command", "command": command,
                                                                   "timeout": 3 if event == "SessionEnd" else 10}]})
            if path.exists() or not remove:
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".deskmate-hooks-", encoding="utf-8", delete=False) as handle:
                        temporary = pathlib.Path(handle.name)
                        json.dump(settings, handle, indent=2)
                        handle.write("\n")
                    os.replace(temporary, path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        for skill, link in skills:
            if remove:
                if link.is_symlink() and link.resolve() == skill.resolve():
                    link.unlink()
            elif not link.is_symlink():
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(skill, target_is_directory=True)
        result["hooks_path"] = str(path)
    except (OSError, UnicodeError, ValueError) as error:
        result.update(status="error", warnings=[str(error)])
    return result
