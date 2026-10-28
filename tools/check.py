#!/usr/bin/env python3
"""Runs the read-only checks listed in the project cards, used by /whats-on-today and /call-it-a-day.

A project card is ~/.claude/projects/<folder-key>/memory/project-card.md, written by /checkpoint.
Its "## Checks" section lists one command per line, as: - <label>: `<command>`

Usage:
  check.py                 every card whose state is not closed
  check.py <card> ...      only these cards
  check.py --all           closed cards too
"""
import pathlib
import re
import subprocess
import sys

PROJECTS = pathlib.Path.home() / ".claude" / "projects"
CHECK = re.compile(r"^- (.+?): `(.+)`\s*$")
STATE = re.compile(r"^- \*\*State:\*\*\s*(\w+)", re.M)
TIMEOUT = 15


def section(text, title):
    m = re.search(rf"^## {title}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def title(text, path):
    m = re.search(r"^\*\*(.+?)\*\*|^# (.+)$", text, re.M)
    return (m.group(1) or m.group(2)).strip(" .") if m else path.parent.parent.name


def run(command):
    try:
        r = subprocess.run(["/bin/zsh", "-c", command], capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "timeout", ""
    out = (r.stdout.strip() or r.stderr.strip()).splitlines()
    return ("ok" if r.returncode == 0 else f"exit {r.returncode}"), (out[0] if out else "")


def main():
    args = [a for a in sys.argv[1:] if a != "--all"]
    cards = [pathlib.Path(a).expanduser() for a in args] or sorted(PROJECTS.glob("*/memory/project-card.md"))
    for card in cards:
        text = card.read_text(encoding="utf-8")
        state = STATE.search(section(text, "Status"))
        if not args and "--all" not in sys.argv and state and state.group(1) == "closed":
            continue
        print(f"== {title(text, card)}  ({state.group(1) if state else 'no status'})")
        checks = [CHECK.match(line) for line in section(text, "Checks").splitlines()]
        checks = [c for c in checks if c]
        if not checks:
            print("   (no checks in the card)")
        for c in checks:
            result, first = run(c.group(2))
            print(f"   {c.group(1)}: {result}" + (f"  {first[:160]}" if first else ""))


if __name__ == "__main__":
    main()
