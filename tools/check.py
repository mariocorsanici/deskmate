#!/usr/bin/env python3
"""Runs the read-only checks listed in the project cards, used by /whats-on-today and /call-it-a-day.

A project card is ~/.claude/projects/<folder-key>/memory/project-card.md, written by /checkpoint.
Its "## Checks" section lists one command per line, as: - <label>: `<command>`

Usage:
  check.py                 every card whose state is not closed or standby
  check.py <card> ...      only these cards, whatever their state
  check.py --all           closed and standby cards too

Standby cards are skipped (their checks can be slow, e.g. SSH to a machine that is off),
but their titles are listed on a last line, so they stay visible.

Before a card's checks, every repo they name with `git -C <folder>` is fetched once, so that
origin/... refs (and checks like `status -sb`) show the remote as it is now, not as of the last pull.
Fetch only updates remote-tracking refs: local branches and files are untouched.
"""
import pathlib
import re
import shlex
import subprocess
import sys

PROJECTS = pathlib.Path.home() / ".claude" / "projects"
CHECK = re.compile(r"^- (.+?): `(.+)`\s*$")
STATE = re.compile(r"^- \*\*State:\*\*\s*(\w+)", re.M)
FETCH = "GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=8' git -C {} fetch --quiet"
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


def repositories(command):
    """Read literal git -C folders, including shell-quoted paths with spaces."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []
    return [str(pathlib.Path(tokens[i + 2]).expanduser())
            for i in range(len(tokens) - 2)
            if tokens[i:i + 2] == ["git", "-C"]]


def main():
    args = [a for a in sys.argv[1:] if a != "--all"]
    cards = [pathlib.Path(a).expanduser() for a in args] or sorted(PROJECTS.glob("*/memory/project-card.md"))
    skip = not args and "--all" not in sys.argv
    standby = []
    fetched = set()
    for card in cards:
        text = card.read_text(encoding="utf-8")
        state = STATE.search(section(text, "Status"))
        if skip and state and state.group(1) == "closed":
            continue
        if skip and state and state.group(1) == "standby":
            standby.append(title(text, card))
            continue
        print(f"== {title(text, card)}  ({state.group(1) if state else 'no status'})")
        checks = [CHECK.match(line) for line in section(text, "Checks").splitlines()]
        checks = [c for c in checks if c]
        if not checks:
            print("   (no checks in the card)")
        for repo in dict.fromkeys(repo for c in checks for repo in repositories(c.group(2))):
            if repo not in fetched:
                fetched.add(repo)
                result, first = run(FETCH.format(shlex.quote(repo)))
                print(f"   fetch {repo}: {result}" + (f"  {first[:160]}" if first else ""))
        for c in checks:
            result, first = run(c.group(2))
            print(f"   {c.group(1)}: {result}" + (f"  {first[:160]}" if first else ""))
    if standby:
        print(f"In stand-by: {', '.join(standby)}")


if __name__ == "__main__":
    main()
