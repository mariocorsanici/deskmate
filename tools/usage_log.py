#!/usr/bin/env python3
"""Locked, atomic activity CSV updates shared by hooks and usage calculation."""
import csv
import datetime as dt
import fcntl
import os
from pathlib import Path
import sys
import tempfile
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {'checkpoint', 'whats-on-today', 'call-it-a-day', 'how-did-it-go', 'study-later'}
LEGACY_COLUMNS = ['date', 'time', 'weekday', 'event', 'detail', 'session', 'cwd',
                  'turns', 'input_tokens', 'cache_tokens', 'output_tokens']
COLUMNS = [*LEGACY_COLUMNS, 'usage_scope']


def data_root():
    return Path(os.environ.get('DESKMATE_DATA_DIR', ROOT / 'data')).expanduser()


@contextmanager
def locked(data):
    data.mkdir(parents=True, exist_ok=True)
    with (data / '.log.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield data / 'log.csv'


def read_log(path):
    if not path.exists():
        return list(COLUMNS), []
    with path.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream, strict=True)
        fields = reader.fieldnames
        if (not fields or len(set(fields)) != len(fields)
                or not set(LEGACY_COLUMNS).issubset(fields)):
            raise ValueError('unrecognized activity CSV header')
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError('activity CSV column count does not match header')
    fields = [*fields, *([] if 'usage_scope' in fields else ['usage_scope'])]
    for row in rows:
        row.setdefault('usage_scope', '')
        if row['event'] in SKILLS and not row['usage_scope']:
            row['usage_scope'] = 'legacy-window'
    return fields, rows


def atomic_write(path, fields, rows):
    fd, name = tempfile.mkstemp(prefix='.log-', suffix='.tmp', dir=path.parent)
    try:
        if path.exists():
            os.fchmod(fd, path.stat().st_mode & 0o777)
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def append_event(event, detail='', session='', cwd=''):
    now = dt.datetime.now().astimezone()
    if event in {skill + '-end' for skill in SKILLS} and not detail:
        detail = now.astimezone(dt.timezone.utc).isoformat(timespec='microseconds')
    with locked(data_root()) as path:
        fields, rows = read_log(path)
        value = dict.fromkeys(fields, '')
        value.update(date=now.strftime('%Y-%m-%d'), time=now.strftime('%H:%M'),
                     weekday='mon tue wed thu fri sat sun'.split()[now.weekday()],
                     event=event, detail=detail, session=session, cwd=cwd,
                     usage_scope='legacy-window' if event in SKILLS else '')
        rows.append(value)
        atomic_write(path, fields, rows)


def main():
    args = (sys.argv[1:] + [''] * 4)[:4]
    if not args[0]:
        print('usage: log_event.sh <event> [detail] [session] [cwd]', file=sys.stderr)
        return 2
    try:
        append_event(*args)
        return 0
    except (OSError, ValueError, csv.Error) as error:
        print(f'activity log: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
