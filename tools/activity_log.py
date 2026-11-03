#!/usr/bin/env python3
"""Provider-aware activity CSV storage and atomic legacy migration (stdlib only)."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import datetime as dt
import fcntl
import io
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LEGACY_COLUMNS = ['date', 'time', 'weekday', 'event', 'detail', 'session', 'cwd',
                  'turns', 'input_tokens', 'cache_tokens', 'output_tokens']
COLUMNS = [*LEGACY_COLUMNS, 'schema_version', 'provider']
PROVIDERS = ('claude', 'codex')


def data_root():
    return Path(os.environ.get('DESKMATE_DATA_DIR', ROOT / 'data')).expanduser()


@contextmanager
def locked():
    data = data_root()
    # Reject unsupported data before creating directories or a lock file.
    read_log(data / 'log.csv')
    data.mkdir(parents=True, exist_ok=True)
    with (data / '.log.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield data / 'log.csv'


def read_log(path):
    """Read/validate without mutation; legacy provider attribution is in memory."""
    if not path.exists():
        return list(COLUMNS), [], False
    reader = csv.DictReader(io.StringIO(path.read_text(encoding='utf-8'), newline=''), strict=True)
    fields = reader.fieldnames
    if (not fields or len(fields) != len(set(fields))
            or not set(LEGACY_COLUMNS).issubset(fields)):
        raise ValueError('unrecognized log schema: required CSV columns are missing or duplicated')
    legacy = 'schema_version' not in fields and 'provider' not in fields
    if not legacy and not {'schema_version', 'provider'}.issubset(fields):
        raise ValueError('unrecognized log schema: provider and schema_version are required together')
    rows = list(reader)
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError('invalid log CSV row: column count does not match header')
        if legacy:
            row.update(schema_version='1', provider='claude')
        elif row['schema_version'] != '1':
            raise ValueError(f"unsupported log schema {row['schema_version']}")
        if row['provider'] not in PROVIDERS:
            raise ValueError(f"unknown log provider {row['provider']}")
    return [*fields, *(['schema_version', 'provider'] if legacy else [])], rows, legacy


def atomic_write(path, fields, rows):
    """Replace only after a complete, flushed CSV is ready on the same filesystem."""
    fd, temporary = tempfile.mkstemp(prefix='.log-', suffix='.tmp', dir=path.parent)
    try:
        if path.exists():
            os.fchmod(fd, path.stat().st_mode & 0o777)
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def backup(path):
    """Never replace an earlier migration backup."""
    content = path.read_bytes()
    index = 0
    while True:
        target = path.with_name(path.name + '.bak' + (f'.{index}' if index else ''))
        try:
            with target.open('xb') as stream:
                os.chmod(target, 0o600)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            return target
        except FileExistsError:
            index += 1


def migrate_locked(path):
    fields, rows, legacy = read_log(path)
    saved = backup(path) if legacy else None
    if legacy:
        atomic_write(path, fields, rows)
    return fields, rows, saved


def append_event(event, detail='', session='', cwd='', provider='claude'):
    if provider not in PROVIDERS:
        raise ValueError(f'unknown log provider {provider}')
    with locked() as path:
        fields, rows, _ = migrate_locked(path)
        now = dt.datetime.now()
        row = dict.fromkeys(fields, '')
        row.update(date=now.strftime('%Y-%m-%d'), time=now.strftime('%H:%M'),
                   weekday='mon tue wed thu fri sat sun'.split()[now.weekday()],
                   event=event, detail=detail, session=session, cwd=cwd,
                   schema_version='1', provider=provider)
        rows.append(row)
        atomic_write(path, fields, rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['event', 'migrate'])
    parser.add_argument('event', nargs='?')
    parser.add_argument('detail', nargs='?', default='')
    parser.add_argument('session', nargs='?', default='')
    parser.add_argument('cwd', nargs='?', default='')
    parser.add_argument('--provider', choices=PROVIDERS, default='claude')
    args = parser.parse_args()
    try:
        if args.operation == 'event':
            if not args.event:
                parser.error('event required')
            append_event(args.event, args.detail, args.session, args.cwd, args.provider)
        else:
            with locked() as path:
                _, rows, saved = migrate_locked(path)
            print(json.dumps({'schema_version': 1, 'rows': len(rows),
                              'migrated': saved is not None, 'backup': str(saved) if saved else None}))
        return 0
    except (ValueError, OSError, csv.Error) as error:
        print(f'activity log: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
