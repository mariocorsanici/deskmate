#!/usr/bin/env python3
"""Read-only, progressive retrospective: durable evidence before selected deltas."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import datetime as dt
import importlib
import json
from pathlib import Path
import re
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activity_log
import metrics
import project_cards
import session_delta

READ_ERRORS = (OSError, UnicodeError, ValueError, sqlite3.Error, ImportError, csv.Error)


def in_period(stamp, since):
    return isinstance(stamp, str) and stamp[:10] >= since


def document(path, warnings):
    try:
        return {'path': str(path), 'text': path.read_text(encoding='utf-8')}
    except (OSError, UnicodeError):
        warnings.append(f'Durable document unreadable: {path}')
        return None


def durable_state(since):
    root = project_cards.data_root()
    warnings = []
    cards = []
    for path in sorted((root / 'projects').glob('*/project-card.md')):
        try:
            text, metadata = project_cards.read_card(path)
            if metadata:
                cards.append({'path': str(path), 'text': text, 'metadata': metadata})
        except (OSError, UnicodeError, ValueError):
            warnings.append(f'Project card unreadable or invalid: {path}')
    handoffs = []
    paths = sorted((root / 'archive').glob('*.md'))
    if (root / 'handoff.md').exists():
        paths.append(root / 'handoff.md')
    for path in paths:
        # Archive names or their headings identify the Handoff date. Unknown
        # dates remain visible as uncertain evidence rather than disappearing.
        date = re.search(r'\d{4}-\d{2}-\d{2}', path.name)
        if date and date[0] < since:
            continue
        item = document(path, warnings)
        if item is None:
            continue
        if not date:
            date = re.search(r'^#+ .*?(\d{4}-\d{2}-\d{2})', item['text'], re.M)
            if date and date[1] < since:
                continue
        item['date'] = date[0] if date and date.lastindex is None else date[1] if date else None
        if item['date'] is None:
            warnings.append(f'Handoff date unknown: {path}')
        handoffs.append(item)
    try:
        _, rows, _ = activity_log.read_log(root / 'log.csv')
        rows = [row for row in rows if in_period(row['date'], since)]
    except READ_ERRORS:
        rows = []
        warnings.append('Activity log unreadable or unsupported; logged activity is unavailable.')
    return {'cards': cards, 'handoffs': handoffs, 'events': rows}, warnings


def candidate_view(since, durable, warnings):
    """Discover metadata and merge durable identities without opening messages."""
    records = {}
    parts = {}

    def add(provider, record, source):
        sid = record.get('id')
        if not isinstance(sid, str) or not sid:
            warnings.extend(f'{provider}: {w}' for w in record.get('warnings', []))
            return
        key = provider + ':' + sid
        item = records.setdefault(key, {'key': key, 'provider': provider, 'id': sid,
            'cwd': None, 'start': None, 'end': None, 'usage': {}, 'status': 'unavailable',
            'warnings': [], 'sources': [], 'events': []})
        for field in ('cwd', 'start', 'end', 'status'):
            if record.get(field) is not None and (source != 'cached-snapshot' or not item.get(field)
                                                   or item.get(field) == 'unavailable'):
                item[field] = record[field]
        if record.get('usage'):
            item['usage'] = record['usage']
            item['usage_source'] = source
            item['usage_as_of'] = record.get('end') or record.get('start')
        item['warnings'] = list(dict.fromkeys([*item['warnings'], *record.get('warnings', [])]))
        if source not in item['sources']:
            item['sources'].append(source)
        return item

    for provider in activity_log.PROVIDERS:
        events = [r for r in durable['events'] if r['provider'] == provider]
        for row in events:
            if row['session']:
                item = add(provider, {'id': row['session'], 'cwd': row['cwd'] or None,
                                      'end': row['date'] + 'T' + row['time']}, 'activity-log')
                item['events'].append(row['event'])
        for card in durable['cards']:
            metadata = card['metadata']
            if metadata['provider'] != provider:
                continue
            # An old card belongs in durable evidence but does not alone make
            # an inactive Work session a candidate for this period.
            checkpoint = re.search(r'^Checkpoint ([^,\n]+), session `([^`]+)`', card['text'], re.M)
            key = provider + ':' + metadata['session_id']
            if key in records or (checkpoint and checkpoint[2] == metadata['session_id']
                                  and in_period(checkpoint[1], since)):
                item = add(provider, {'id': metadata['session_id']}, 'project-card')
                item['card'] = card['path']
        try:
            cached = metrics.usage_records(provider)
        except READ_ERRORS:
            cached = {}
            warnings.append(f'{provider}: cached native usage unavailable or unsupported.')
        try:
            implementation = importlib.import_module('adapter_' + provider)
            for record in implementation.discover(since):
                add(provider, record, 'native-metadata')
        except READ_ERRORS:
            warnings.append(f'{provider}: session discovery unavailable; showing durable identities.')
        # Saved usage is a snapshot, not refreshed by reading a transcript here.
        for sid, record in cached.items():
            if (any(record.get(field) is not None and not isinstance(record[field], str)
                    for field in ('cwd', 'start', 'end'))
                    or not isinstance(record.get('warnings', []), list)
                    or any(not isinstance(w, str) for w in record.get('warnings', []))
                    or not isinstance(record.get('status', 'ok'), str)):
                warnings.append(f'{provider}:{sid}: malformed cached metadata omitted.')
                continue
            if provider + ':' + sid in records or in_period(record.get('end') or record.get('start'), since):
                add(provider, {**record, 'status': 'cached'}, 'cached-snapshot')
        parts[provider] = {'events': dict(sorted(Counter(r['event'] for r in events).items())),
                           'sessions': []}

    candidates = sorted(records.values(), key=lambda item: item['key'])
    for item in candidates:
        reasons = []
        if item['events']:
            reasons.append('Logged Daily loop activity: ' + ', '.join(sorted(set(item['events']))))
        # Discovery may have added this identity after the card pass.
        for card in durable['cards']:
            metadata = card['metadata']
            if metadata['provider'] == item['provider'] and metadata['session_id'] == item['id']:
                item['card'] = card['path']
                reasons.append('Owns a shared Project card; compare its Checkpoint with the Handoff')
        if item['status'] in ('degraded', 'unavailable'):
            reasons.append('Incomplete metadata; clarify the session only if relevant')
        if not reasons:
            reasons.append('Recent native Work session in the retrospective period')
        item['reasons'] = reasons
        parts[item['provider']]['sessions'].append({key: item[key] for key in
            ('provider', 'id', 'cwd', 'start', 'end', 'usage', 'status', 'warnings',
             'usage_source', 'usage_as_of') if key in item})
    ranked = sorted(candidates, key=lambda item: (
        bool(item['events']), 'card' in item, item['end'] or '', item['key']), reverse=True)
    recommendations = [{'key': item['key'], 'provider': item['provider'],
                        'id': item['id'], 'reasons': item['reasons']} for item in ranked[:5]]
    return candidates, recommendations, {'providers': parts,
        'usage_source': 'metadata-and-cached-snapshots',
        'note': 'Raw native counters remain separate by Provider; snapshots may be stale and are not refreshed here.'}


def unavailable(provider, sid, messages, characters):
    result = session_delta.Selection(provider, sid, messages, characters, None)
    return result.result({'status': 'degraded', 'warnings': [
        'Session delta adapter unavailable; continue from durable evidence.']})


def report(since, *, selected=(), deepen=None, max_messages=None, max_characters=None):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', since):
        raise ValueError('--since must use YYYY-MM-DD')
    dt.date.fromisoformat(since)
    if deepen and selected:
        raise ValueError('--deepen and --select cannot be combined')
    override = max_messages is not None or max_characters is not None
    if bool(deepen) != override:
        raise ValueError('--deepen requires explicit one-off limits; limit overrides require --deepen')
    messages, characters = session_delta.configured_limits(max_messages, max_characters)
    selection = list(dict.fromkeys([deepen] if deepen else selected))
    durable, warnings = durable_state(since)
    candidates, recommendations, usage = candidate_view(since, durable, warnings)
    by_key = {item['key']: item for item in candidates}
    for key in selection:
        if key not in by_key:
            raise ValueError(f'Unknown candidate {key!r}; select a listed Provider:ID')
    deltas = []
    for key in selection:
        item = by_key[key]
        try:
            adapter = importlib.import_module('adapter_' + item['provider'])
            delta = adapter.read_delta(item['id'], max_messages=messages, max_characters=characters)
        except READ_ERRORS:
            delta = unavailable(item['provider'], item['id'], messages, characters)
        deltas.append(delta)
    return {'schema_version': 1, 'since': since,
            'phase': 'deepening' if deepen else 'analysis' if selection else 'selection',
            'durable': durable, 'metrics': usage, 'candidates': candidates,
            'recommendations': recommendations, 'selected': selection, 'deltas': deltas,
            'warnings': warnings}


def render(result):
    lines = [f"Retrospective since {result['since']} — {result['phase']}",
             'Durable evidence (plans and saved state; verify conclusions against current facts):']
    for kind in ('cards', 'handoffs'):
        for item in result['durable'][kind]:
            lines.extend([f"{kind}: {item['path']}", item['text']])
    lines.append('Activity log: ' + json.dumps(result['durable']['events']))
    lines.append('Raw metrics by Provider (metadata/cached snapshots; no transcript refresh):')
    for provider, part in result['metrics']['providers'].items():
        lines.append(provider + ': ' + json.dumps(part))
    lines.append('Candidates (all; identities are Provider:ID):')
    for item in result['candidates']:
        lines.append(f"  {item['key']} | {item['cwd'] or 'unknown folder'} | "
                     f"{item['end'] or 'unknown activity time'} | {item['status']}")
    if not result['candidates']:
        lines.append('  none available')
    lines.append('Recommended (at most five; user may add, remove or replace):')
    for item in result['recommendations']:
        lines.append('  ' + item['key'] + ': ' + '; '.join(item['reasons']))
    lines.append('After user selection, repeat with --select PROVIDER:ID for each chosen session; '
                 'omitting --select reads no deltas. Deepen one session with --deepen PROVIDER:ID '
                 'and explicit --max-messages N and/or --max-characters N.')
    lines.extend(session_delta.render(delta) for delta in result['deltas'])
    lines.extend('warning: ' + warning for warning in result['warnings'])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--since', required=True)
    parser.add_argument('--select', action='append', default=[])
    parser.add_argument('--deepen', action='append', default=[])
    parser.add_argument('--max-messages', type=int)
    parser.add_argument('--max-characters', type=int)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args()
    try:
        if len(args.deepen) > 1:
            raise ValueError('Deepen only one Work session at a time')
        result = report(args.since, selected=args.select, deepen=args.deepen[0] if args.deepen else None,
                        max_messages=args.max_messages, max_characters=args.max_characters)
        print(json.dumps(result) if args.format == 'json' else render(result))
        return 0
    except READ_ERRORS as error:
        print(f'retrospective: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
