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
import pathlib
import re

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
LOG = DATA / "log.csv"
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
COLUMNS = ["date", "time", "weekday", "event", "detail", "session", "cwd",
           "turns", "input_tokens", "cache_tokens", "output_tokens"]
COMMAND = re.compile(r"^\s*<command-name>/?([^<]+)</command-name>")


def read_transcript(path):
    """Returns the commands run [(ts, name)] and the usage [(ts, input, cache, output)]."""
    commands, usage, seen = [], [], set()
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = r.get("timestamp")
        msg = r.get("message") or {}
        if r.get("type") == "user" and not r.get("isMeta") and isinstance(msg.get("content"), str):
            m = COMMAND.match(msg["content"])
            if m:
                commands.append((ts, m.group(1).strip()))
        elif r.get("type") == "assistant" and msg.get("usage") and msg.get("id") not in seen:
            seen.add(msg.get("id"))
            u = msg["usage"]
            usage.append((ts, u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                          u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0)))
    return commands, usage


def compute(session, rows):
    found = list(PROJECTS.glob(f"*/{session}.jsonl"))
    if not found:
        return
    commands, usage = read_transcript(found[0])
    used = set()
    for row in rows:
        # the k-th run of a skill in the log matches the k-th one in the transcript
        index = next((i for i, (_, name) in enumerate(commands)
                      if name == row["event"] and i not in used), None)
        if index is None:
            continue
        used.add(index)
        start = commands[index][0]
        end = commands[index + 1][0] if index + 1 < len(commands) else "9999"
        part = [u for u in usage if start <= u[0] < end]
        row["turns"] = str(len(part))
        for name, pos in (("input_tokens", 1), ("cache_tokens", 2), ("output_tokens", 3)):
            row[name] = str(sum(u[pos] for u in part))


def main():
    global PROJECTS
    p = argparse.ArgumentParser()
    p.add_argument("--session")
    p.add_argument("--projects", type=pathlib.Path, help="transcripts folder (for tests)")
    a = p.parse_args()
    PROJECTS = a.projects or PROJECTS
    if not LOG.exists():
        return
    with (DATA / ".log.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with LOG.open(newline="") as f:
            rows = list(csv.DictReader(f))
        by_session = {}
        for r in rows:
            if r.get("session") and not r["event"].endswith("-reminder"):
                by_session.setdefault(r["session"], []).append(r)
        for session, group in by_session.items():
            if a.session in (None, session):
                compute(session, group)
        with LOG.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows({k: (r.get(k) or "") for k in COLUMNS} for r in rows)


if __name__ == "__main__":
    main()
