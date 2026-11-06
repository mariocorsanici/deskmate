#!/usr/bin/env python3
"""Fill skill usage until its precise end marker or the legacy command boundary.

An end-marked window excludes unrelated work after completion. Historical runs
without a valid marker keep the next-command/session-end window, labeled
legacy-window. Neither scope claims to include a final reply after the marker.
"""
import argparse
import csv
import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from usage_log import COLUMNS, SKILLS, atomic_write, data_root, locked, read_log

DATA = data_root()
LOG = DATA / 'log.csv'
PROJECTS = pathlib.Path.home() / '.claude' / 'projects'
COMMAND = re.compile(r'^\s*(?:<command-message>[^<]*</command-message>\s*)?<command-name>/?([^<]+)</command-name>')


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def read_transcript(path):
    """Return normalized command boundaries and deduplicated native usage."""
    commands, usage, seen = [], [], set()
    with path.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get('isSidechain') or record.get('isMeta'):
                continue
            stamp, message = timestamp(record.get('timestamp')), record.get('message')
            if stamp is None or not isinstance(message, dict):
                continue
            content = message.get('content')
            if record.get('type') == 'user' and isinstance(content, str):
                match = COMMAND.match(content)
                if match:
                    commands.append((stamp, match.group(1).strip()))
            if record.get('type') != 'assistant':
                continue
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get('type') != 'tool_use' or block.get('name') != 'Skill':
                        continue
                    arguments = block.get('input')
                    if isinstance(arguments, dict) and isinstance(arguments.get('skill'), str):
                        commands.append((stamp, arguments['skill']))
            counters, identity = message.get('usage'), message.get('id')
            if not isinstance(counters, dict):
                continue
            if isinstance(identity, str):
                if identity in seen:
                    continue
                seen.add(identity)
            def count(key):
                value = counters.get(key, 0)
                return value if type(value) is int and value >= 0 else 0
            usage.append((stamp, count('input_tokens') + count('cache_creation_input_tokens'),
                          count('cache_read_input_tokens'), count('output_tokens')))
    return commands, usage


def marker_after(rows, row_index, session, start, end):
    current = rows[row_index]
    for candidate in rows[row_index + 1:]:
        if candidate.get('session') != session:
            continue
        if candidate.get('event') in SKILLS:
            break  # another invocation owns any later completion marker
        if (candidate.get('event') != current['event'] + '-end'
                or candidate.get('cwd') != current.get('cwd')):
            continue
        stamp = timestamp(candidate.get('detail'))
        if stamp is not None and start <= stamp < end:
            return stamp
    return None


def compute(session, rows):
    own = [row for row in rows if row.get('session') == session and row.get('event') in SKILLS]
    for row in own:
        row.setdefault('usage_scope', 'legacy-window')
        if not row['usage_scope']:
            row['usage_scope'] = 'legacy-window'
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', session):
        return
    paths = list(PROJECTS.glob(f'*/{session}.jsonl'))
    if len(paths) != 1:
        return
    try:
        commands, usage = read_transcript(paths[0])
    except OSError:
        return
    consumed = -1
    for row_index, row in enumerate(rows):
        if row.get('session') != session or row.get('event') not in SKILLS:
            continue
        index = next((i for i in range(consumed + 1, len(commands))
                      if commands[i][1] == row['event']), None)
        if index is None:
            continue
        consumed = index
        start = commands[index][0]
        end = commands[index + 1][0] if index + 1 < len(commands) else float('inf')
        marked = marker_after(rows, row_index, session, start, end)
        row['usage_scope'] = 'end-marked' if marked is not None else 'legacy-window'
        if marked is not None:
            end = marked
        part = [entry for entry in usage if start <= entry[0] < end]
        row['turns'] = str(len(part))
        for name, pos in (('input_tokens', 1), ('cache_tokens', 2), ('output_tokens', 3)):
            row[name] = str(sum(entry[pos] for entry in part))


def main():
    global PROJECTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session')
    parser.add_argument('--projects', type=pathlib.Path, help='transcripts folder (for tests)')
    args = parser.parse_args()
    PROJECTS = args.projects or PROJECTS
    if not LOG.exists():
        return 0
    try:
        with locked(DATA) as path:
            fields, rows = read_log(path)
            by_session = {}
            for row in rows:
                if row.get('session'):
                    by_session.setdefault(row['session'], []).append(row)
            for session, group in by_session.items():
                if args.session in (None, session):
                    compute(session, group)
            atomic_write(path, fields, rows)
        return 0
    except (OSError, ValueError, csv.Error) as error:
        print(f'token usage: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
