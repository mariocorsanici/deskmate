#!/usr/bin/env python3
"""Fills in data/log.csv the tokens used by each Claude run of the deskmate skills.

A run starts at its command (/call-it-a-day, ...). It ends at the skill's precise
`<skill>-end` marker when one was logged (usage_scope end-marked), which excludes
unrelated work after completion. Historical runs without a valid marker keep the
next-command/session-end window (usage_scope legacy-window), which includes the
user's replies inside the skill. Neither scope claims a final reply after the
marker. Tokens come from the usage field of Claude's messages in the transcript.

Usage:
  token_usage.py                  # every session in the log
  token_usage.py --session <id>   # just one (used by the Stop hook)
"""
import argparse
import csv
import datetime as dt
import fcntl
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import activity_log
from adapter_claude import timestamp
from provider_environment import claude_home

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get("DESKMATE_DATA_DIR", ROOT / "data"))
LOG = DATA / "log.csv"
PROJECTS = claude_home() / "projects"
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
            if row.get("isSidechain"):
                continue  # subagent traffic is not a run of the parent skill
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


def marker_timestamp(value):
    """A marker counts only with an explicit offset, as append_event writes it."""
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def marker_after(rows, row_index, session, start, end):
    """The timestamp of this run's own end marker inside [start, end), or None."""
    current = rows[row_index]
    for candidate in rows[row_index + 1:]:
        if candidate.get("session") != session:
            continue
        if candidate.get("event") in activity_log.SKILLS:
            break  # another invocation owns any later completion marker
        if (candidate.get("event") != current["event"] + "-end"
                or candidate.get("cwd") != current.get("cwd")):
            continue
        stamp = marker_timestamp(candidate.get("detail"))
        if stamp is not None and start <= stamp < end:
            return stamp
    return None


def compute(session, rows):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", session):
        return
    found = list(PROJECTS.glob(f"*/{session}.jsonl"))
    if len(found) != 1:
        return
    try:
        commands, usage = read_transcript(found[0])
    except (OSError, UnicodeError):
        print('token usage: warning: transcript unavailable; per-skill attribution skipped.', file=sys.stderr)
        return
    consumed = -1
    for row_index, row in enumerate(rows):
        if row["event"] not in activity_log.SKILLS:
            continue
        # runs match in order: the next transcript command of the same skill
        index = next((i for i in range(consumed + 1, len(commands))
                      if commands[i][1] == row["event"]), None)
        if index is None:
            continue
        consumed = index
        start = commands[index][0]
        end = commands[index + 1][0] if index + 1 < len(commands) else float("inf")
        marked = marker_after(rows, row_index, session, start, end)
        row["usage_scope"] = "end-marked" if marked is not None else "legacy-window"
        if marked is not None:
            end = marked
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
