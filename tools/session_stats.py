#!/usr/bin/env python3
"""Data for the experiment "resume yesterday's session or start a new one" (config.json, experiments.fresh_sessions).

For each work session and day: whether the session was resumed (started on an earlier day) or new,
the context Claude carried into the first answer of the day, the tokens used, the compactions,
and the resume rating given at /checkpoint (rows "resume-rating" in data/log.csv). Then a summary per mode.

Usage:
  session_stats.py                    from the experiment's start date
  session_stats.py --since 2026-10-23
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get("DESKMATE_DATA_DIR", ROOT / "data"))
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
MIN_TURNS = 5  # fewer answers in a day: a quick look, not a work session


def local_day(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date()


def read(path):
    """Returns (first day, cwd, {day: stats})."""
    first, cwd, seen = None, None, set()
    days = collections.defaultdict(lambda: {"turns": 0, "tokens": 0, "first_context": None, "compactions": 0})
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = r.get("timestamp")
        if not ts or r.get("isSidechain"):
            continue
        day = local_day(ts)
        msg = r.get("message") or {}
        if r.get("type") == "user":
            cwd = cwd or r.get("cwd")
            first = first or day
            content = msg.get("content")
            if r.get("isCompactSummary") or (isinstance(content, str)
                                             and content.startswith("This session is being continued")):
                days[day]["compactions"] += 1
        elif r.get("type") == "assistant" and msg.get("usage") and msg.get("id") not in seen:
            seen.add(msg.get("id"))
            u = msg["usage"]
            context = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
            d = days[day]
            d["turns"] += 1
            d["tokens"] += context + u.get("output_tokens", 0)
            if d["first_context"] is None:
                d["first_context"] = context
    return first, cwd, days


def ratings():
    try:
        with (DATA / "log.csv").open(newline="") as f:
            return {(r["date"], r["session"]): r["detail"] for r in csv.DictReader(f) if r["event"] == "resume-rating"}
    except FileNotFoundError:
        return {}


def main():
    try:
        experiment = json.loads((DATA / "config.json").read_text()).get("experiments", {}).get("fresh_sessions", {})
    except FileNotFoundError:
        experiment = {}
    p = argparse.ArgumentParser()
    p.add_argument("--since", default=experiment.get("since", dt.date.today().isoformat()), help="first day, YYYY-MM-DD")
    a = p.parse_args()
    since = dt.date.fromisoformat(a.since)
    threshold = dt.datetime.combine(since, dt.time()).timestamp()
    rated = ratings()

    rows = []
    for f in PROJECTS.glob("*/*.jsonl"):
        if f.stat().st_mtime < threshold:
            continue
        first, cwd, days = read(f)
        if not first or cwd == str(pathlib.Path.home()):  # sessions from ~ run deskmate, not project work
            continue
        for day, d in days.items():
            if day < since or d["turns"] < MIN_TURNS:
                continue
            mode = "resume" if first < day else "new"
            rows.append((day, mode, f.stem, pathlib.Path(cwd).name, d, rated.get((day.isoformat(), f.stem), "")))

    print(f"{'day':<10} {'mode':<6} {'session':<8} {'project':<24} {'ctx@start':>9} {'turns':>5} {'tokens':>7} {'compact':>7} {'rating':>6}")
    for day, mode, sid, project, d, rating in sorted(rows):
        print(f"{day.strftime('%d/%m %a'):<10} {mode:<6} {sid[:8]:<8} {project[:24]:<24} {d['first_context'] // 1000:>8}k "
              f"{d['turns']:>5} {d['tokens'] / 1e6:>6.1f}M {d['compactions']:>7} {rating:>6}")

    print("\nper mode")
    target = experiment.get("target_days", 5)
    for mode in ("resume", "new"):
        part = [r for r in rows if r[1] == mode]
        if not part:
            print(f"  {mode:<6} no days yet (target {target})")
            continue
        n = len(part)
        scores = [int(r[5]) for r in part if r[5].isdigit()]
        rating = f"rating {sum(scores) / len(scores):.1f} ({len(scores)} given)" if scores else "no ratings yet"
        print(f"  {mode:<6} {n} session-days (target {target})"
              f" · context at start {sum(r[4]['first_context'] for r in part) // n // 1000}k"
              f" · tokens per answer {sum(r[4]['tokens'] for r in part) / sum(r[4]['turns'] for r in part) / 1000:.0f}k"
              f" · compactions {sum(r[4]['compactions'] for r in part)} · {rating}")


if __name__ == "__main__":
    main()
