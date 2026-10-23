#!/usr/bin/env python3
"""Text summary of the Claude Code sessions active in a range of days.

Reads the transcripts in ~/.claude/projects/*/*.jsonl (main sessions only,
not subagents) and prints, for each session touched in the period, its
folder, times, the command to resume it and its latest text messages.

Usage:
  sessions.py                       # sessions touched today, last 8 messages
  sessions.py --since 2026-10-21    # from that day until today
  sessions.py --messages 40         # more messages per session (retrospective)
"""
import argparse
import datetime as dt
import json
import pathlib
import re

PROJECTS = pathlib.Path.home() / ".claude" / "projects"
COMMAND = re.compile(r"<command-name>(.*?)</command-name>.*?(?:<command-args>(.*?)</command-args>)?", re.S)


def user_text(content):
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if b.get("type") == "text"]
        content = "\n".join(parts)
    if not content:
        return None
    m = COMMAND.search(content)
    if m:
        return f"{m.group(1)} {m.group(2) or ''}".strip()
    if content.lstrip().startswith("<"):
        return None
    return content


def assistant_text(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if b.get("type") == "text") or None


def read(path):
    s = {"id": path.stem, "cwd": None, "start": None, "end": None, "messages": []}
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("isSidechain") or r.get("isMeta") or r.get("type") not in ("user", "assistant"):
            continue
        s["cwd"] = s["cwd"] or r.get("cwd")  # starting folder: the one to run --resume from
        ts = r.get("timestamp")
        if ts:
            s["start"] = s["start"] or ts
            s["end"] = ts
        content = r.get("message", {}).get("content")
        text = user_text(content) if r["type"] == "user" else assistant_text(content)
        if text:
            s["messages"].append(("USER" if r["type"] == "user" else "CLAUDE", ts, text.strip()))
    return s


def local_time(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%d/%m %H:%M")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", default=dt.date.today().isoformat(), help="first day, YYYY-MM-DD")
    p.add_argument("--messages", type=int, default=8, help="last N messages per session")
    p.add_argument("--cut", type=int, default=700, help="max characters per message")
    a = p.parse_args()

    threshold = dt.datetime.combine(dt.date.fromisoformat(a.since), dt.time()).timestamp()
    files = sorted((f for f in PROJECTS.glob("*/*.jsonl") if f.stat().st_mtime >= threshold),
                   key=lambda f: f.stat().st_mtime)
    for f in files:
        s = read(f)
        prompts = [m for m in s["messages"] if m[0] == "USER"]
        if not prompts or dt.datetime.fromisoformat(s["end"].replace("Z", "+00:00")).timestamp() < threshold:
            continue
        print("=" * 80)
        print(f"SESSION {s['id']}")
        print(f"folder:  {s['cwd']}")
        print(f"active:  {local_time(s['start'])} -> {local_time(s['end'])}  ({len(prompts)} prompts)")
        print(f"resume:  cd {s['cwd']} && claude --resume {s['id']}")
        print(f"first prompt: {prompts[0][2][:300]}")
        print("-" * 80)
        for who, ts, text in (s["messages"][-a.messages:] if a.messages else []):
            short = text if len(text) <= a.cut else text[: a.cut] + " […]"
            print(f"[{local_time(ts)}] {who}: {short}\n")


if __name__ == "__main__":
    main()
