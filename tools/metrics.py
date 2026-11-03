#!/usr/bin/env python3
"""Structured activity and native usage, always partitioned by Provider."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import datetime as dt
import importlib
import json
import os
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activity_log

USAGE_FIELDS = ('turns', 'input_tokens', 'cache_tokens', 'output_tokens')


def adapter(provider):
    try:
        return importlib.import_module('adapter_' + provider)
    except ModuleNotFoundError as error:
        if error.name == 'adapter_' + provider:
            return None
        raise


RECORD_FIELDS = ('provider', 'id', 'cwd', 'start', 'end', 'usage', 'status', 'warnings')


def usage_records(provider):
    path = activity_log.data_root() / 'usage' / (provider + '.json')
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or type(payload.get('schema_version')) is not int or payload.get('schema_version') != 1:
        raise ValueError('unsupported raw usage schema')
    if payload.get('provider') != provider or not isinstance(payload.get('sessions'), dict):
        raise ValueError('invalid raw usage provider or sessions')
    records = payload['sessions']
    for sid, record in records.items():
        if (not isinstance(record, dict) or record.get('provider') != provider
                or record.get('id') != sid or not isinstance(record.get('usage'), dict)
                or set(record) - set(RECORD_FIELDS)):
            raise ValueError('invalid raw usage session identity')
    return records


def native_usage(provider, session_id):
    implementation = adapter(provider)
    if implementation is None:
        return None
    record = implementation.read_usage(session_id)
    return {key: record[key] for key in RECORD_FIELDS if key in record}


def update_session_usage(provider, session_id):
    """Snapshot native counters, replacing rather than accumulating repeated Stop events."""
    record = native_usage(provider, session_id)
    if not record or not record.get('usage'):
        return
    # Validate before mutation, then serialize with the same lock as the CSV.
    usage_records(provider)
    with activity_log.locked():
        records = usage_records(provider)
        records[session_id] = record
        directory = activity_log.data_root() / 'usage'
        directory.mkdir(exist_ok=True)
        path = directory / (provider + '.json')
        fd, temporary = tempfile.mkstemp(prefix='.' + provider + '-', suffix='.tmp', dir=directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'schema_version': 1, 'provider': provider, 'sessions': records}, stream, sort_keys=True)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def report(providers, since):
    path = activity_log.data_root() / 'log.csv'
    _, rows, _ = activity_log.read_log(path)
    output = {'schema_version': 1, 'providers': {}}
    for provider in providers:
        part = [r for r in rows if r['provider'] == provider and r['date'] >= since]
        sessions = {r['session']: {'provider': provider, 'id': r['session'],
                                  'cwd': r['cwd'], 'usage': {}, 'status': 'unavailable'}
                    for r in part if r['session']}
        for sid, record in usage_records(provider).items():
            if (record.get('end') or record.get('start') or '')[:10] >= since:
                sessions[sid] = {**record, 'status': 'cached'}
        warnings = []
        implementation = adapter(provider)
        if implementation is not None:
            try:
                for record in implementation.discover(since):
                    # The report copies metadata/usage only, never messages or tool output.
                    sid = record.get('id')
                    if sid:
                        previous = sessions.get(sid, {})
                        metadata = {key: record[key] for key in RECORD_FIELDS if key in record}
                        if previous.get('status') == 'cached' and not record.get('usage'):
                            metadata.update(usage=previous['usage'], status='cached')
                        sessions[sid] = metadata
            except (ValueError, OSError) as error:
                warnings.append(f'{provider} usage unavailable: {error}')
        else:
            warnings.append(f'{provider} transcript adapter unavailable; showing logged activity')
        if implementation is not None:
            for sid in list(sessions):
                try:
                    record = native_usage(provider, sid)
                    if record and record.get('usage'):
                        sessions[sid] = record
                except (ValueError, OSError) as error:
                    warnings.append(f'{provider} usage unavailable for {sid}: {error}')
        skill_usage = None
        if provider == 'claude':
            # These are historical Claude per-skill measurements, distinct from
            # each adapter's native session-level usage below.
            skill_usage = {key: sum(int(row[key]) for row in part if row.get(key))
                           for key in USAGE_FIELDS}
        output['providers'][provider] = {
            'events': dict(sorted(Counter(r['event'] for r in part).items())),
            'sessions': sorted(sessions.values(), key=lambda s: s['id']),
            'skill_usage': skill_usage, 'warnings': warnings,
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=(*activity_log.PROVIDERS, 'all'), default='all')
    parser.add_argument('--since', default='1970-01-01')
    args = parser.parse_args()
    try:
        dt.date.fromisoformat(args.since)
        providers = activity_log.PROVIDERS if args.provider == 'all' else (args.provider,)
        print(json.dumps(report(providers, args.since), sort_keys=True))
        return 0
    except (ValueError, OSError, csv.Error) as error:
        print(f'metrics: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
