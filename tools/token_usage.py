#!/usr/bin/env python3
"""Fills in data/log.csv the tokens used by each run of the deskmate skills.

A run lasts from its command (/call-it-a-day, ...) to the next command of the
same session (any /command) or to the end of the session, so it includes the
user's replies inside the skill. Tokens come from the usage field of Claude's
messages in the transcript.

Usage:
  token_usage.py                  # every session in the log
  token_usage.py --session <id>   # just one (used by the Stop hook)
"""
import argparse
import csv
import fcntl
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import activity_log
from adapter_claude import timestamp

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get("DESKMATE_DATA_DIR", ROOT / "data"))
LOG = DATA / "log.csv"
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
COLUMNS = ["date", "time", "weekday", "event", "detail", "session", "cwd",
           "turns", "input_tokens", "cache_tokens", "output_tokens"]
# the transcript stores a typed command as "<command-message>…</command-message>\n<command-name>/name</command-name>"
COMMAND = re.compile(r"^\s*(?:<command-message>[^<]*</command-message>\s*)?<command-name>/?([^<]+)</command-name>")


def read_transcript(path):
    """Returns the commands run [(ts, name)] and the usage [(ts, input, cache, output)]."""
    commands, usage, seen = [], [], set()
    malformed = False
    with path.open(encoding="utf-8", errors="strict") as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except ValueError:
                malformed = True
                continue
            if not isinstance(row, dict):
                malformed = True
                continue
            if row.get("type") not in ("user", "assistant"):
                continue
            msg = row.get("message")
            ts = timestamp(row.get("timestamp"))
            if not isinstance(msg, dict) or ts is None:
                malformed = True
                continue
            content = msg.get("content")
            if content is not None and not isinstance(content, (str, list)):
                malformed = True
            if row["type"] == "user" and not row.get("isMeta") and isinstance(content, str):
                matched = COMMAND.match(content)
                if matched:
                    commands.append((ts, matched.group(1).strip()))
            if row["type"] != "assistant":
                continue
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        malformed = True
                        continue
                    if block.get("type") == "tool_use" and block.get("name") == "Skill":
                        tool_input = block.get("input")
                        skill = tool_input.get("skill") if isinstance(tool_input, dict) else None
                        if isinstance(skill, str) and skill:
                            commands.append((ts, skill))
                        else:
                            malformed = True
            counters = msg.get("usage")
            if counters is None:
                continue
            if not isinstance(counters, dict):
                malformed = True
                continue
            identity = msg.get("id")
            if isinstance(identity, str) and identity in seen:
                continue
            if not counters:
                continue
            if isinstance(identity, str):
                seen.add(identity)
            values = []
            for key in ("input_tokens", "cache_creation_input_tokens",
                        "cache_read_input_tokens", "output_tokens"):
                value = counters.get(key, 0)
                if type(value) is not int or value < 0:
                    malformed = True
                    value = 0
                values.append(value)
            usage.append((ts, values[0] + values[1], values[2], values[3]))
    if malformed:
        print('token usage: warning: malformed transcript fields were omitted.', file=sys.stderr)
    return commands, usage


def compute(session, rows):
    found = list(PROJECTS.glob(f"*/{session}.jsonl"))
    if not found:
        return
    try:
        commands, usage = read_transcript(found[0])
    except (OSError, UnicodeError):
        print('token usage: warning: transcript unavailable; per-skill attribution skipped.', file=sys.stderr)
        return
    used = set()
    for row in rows:
        # the k-th run of a skill in the log matches the k-th one in the transcript
        index = next((i for i, (_, name) in enumerate(commands)
                      if name == row["event"] and i not in used), None)
        if index is None:
            continue
        used.add(index)
        start = commands[index][0]
        end = commands[index + 1][0] if index + 1 < len(commands) else float("inf")
        part = [u for u in usage if start <= u[0] < end]
        row["turns"] = str(len(part))
        for name, pos in (("input_tokens", 1), ("cache_tokens", 2), ("output_tokens", 3)):
            row[name] = str(sum(u[pos] for u in part))


def update_usage(session_id=None):
    if not LOG.exists():
        return 0
    try:
        with activity_log.locked() as log:
            fields, rows, _ = activity_log.migrate_locked(log)
            by_session = {}
            for row in rows:
                # Legacy run attribution is Claude-specific. Never inspect a Codex
                # session just because its native ID matches a Claude ID.
                if (row['provider'] == 'claude' and row.get('session')
                        and not row['event'].endswith('-reminder')):
                    by_session.setdefault(('claude', row['session']), []).append(row)
            for (_, session), group in by_session.items():
                if session_id in (None, session):
                    compute(session, group)
            activity_log.atomic_write(log, fields, rows)
        return 0
    except (ValueError, OSError, csv.Error) as error:
        print(f'token usage: {error}', file=sys.stderr)
        return 2


def main():
    global PROJECTS
    p = argparse.ArgumentParser()
    p.add_argument("--session")
    p.add_argument("--projects", type=pathlib.Path, help="transcripts folder (for tests)")
    a = p.parse_args()
    PROJECTS = a.projects or PROJECTS
    return update_usage(a.session)


if __name__ == "__main__":
    raise SystemExit(main())
