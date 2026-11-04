#!/usr/bin/env python3
"""Route Project continuation and retain evidence of native Work session launch."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_cards as cards
import providers

NATIVE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
LAUNCH_ID = re.compile(r'[a-f0-9]{32}')
STATES = ('prepared', 'submitted', 'confirming', 'confirmed', 'failed', 'conflict')


def read_journal(card):
    path = card.with_name('work-sessions.json')
    if path.is_symlink():
        raise ValueError('Work session journal must be a regular file')
    if not path.exists():
        return {'schema_version': 1, 'attempts': []}
    data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=cards.unique_object)
    if (not isinstance(data, dict) or set(data) != {'schema_version', 'attempts'}
            or type(data['schema_version']) is not int or data['schema_version'] != 1
            or not isinstance(data['attempts'], list)):
        raise ValueError('Unsupported or invalid Work session journal schema')
    seen = set()
    for item in data['attempts']:
        if (not isinstance(item, dict) or set(item) != {
                'launch_id', 'provider', 'mode', 'expected_revision', 'requested_session_id',
                'native_session_id', 'state', 'ended', 'created_at'}
                or not isinstance(item['launch_id'], str) or not LAUNCH_ID.fullmatch(item['launch_id'])
                or item['launch_id'] in seen or item['provider'] not in ('claude', 'codex')
                or item['mode'] not in ('new', 'resume') or item['state'] not in STATES
                or type(item['expected_revision']) is not int or item['expected_revision'] < 0
                or type(item['ended']) is not bool or not isinstance(item['created_at'], str)):
            raise ValueError('Invalid Work session launch attempt')
        for key in ('requested_session_id', 'native_session_id'):
            value = item[key]
            if value is not None and (not isinstance(value, str) or not NATIVE_ID.fullmatch(value)):
                raise ValueError('Invalid native Work session identity')
        if ((item['mode'] == 'new' and item['requested_session_id'] is not None)
                or (item['mode'] == 'resume' and item['requested_session_id'] is None)
                or (item['state'] in ('confirming', 'confirmed') and item['native_session_id'] is None)):
            raise ValueError('Inconsistent Work session launch state')
        seen.add(item['launch_id'])
    return data


def save_journal(card, journal):
    cards.atomic_write(card.with_name('work-sessions.json'),
                       (json.dumps(journal, sort_keys=True) + '\n').encode())


def overlaps(journal):
    return [{key: attempt[key] for key in ('launch_id', 'provider', 'state', 'native_session_id')}
            for attempt in journal['attempts'] if not attempt['ended'] and (
                attempt['state'] != 'failed' or attempt['native_session_id'] is not None)]


def implementation(provider):
    return importlib.import_module('adapter_' + provider)


def provider_config():
    config = providers.read_config()
    selection = config.get('providers')
    if not isinstance(selection, dict) or set(selection) != {'installed', 'default'}:
        raise ValueError('Configure Providers first: deskmate configure')
    installed, default = selection['installed'], selection['default']
    if (not isinstance(installed, list) or not installed
            or any(p not in ('claude', 'codex') for p in installed)
            or len(set(installed)) != len(installed) or default not in installed):
        raise ValueError('Invalid Provider configuration; run deskmate configure')
    return installed, default


def plan_session(folder: str, *, new: bool = False, provider: str | None = None) -> dict:
    if provider is not None and not new:
        raise ValueError('--provider requires --new; changing Provider is an explicit new Work session')
    installed, default = provider_config()
    project, _, card, legacy = cards.identity(folder)
    _, metadata = cards.read_card(card)
    journal = read_journal(card)
    if cards.legacy_kind(legacy, card) == 'regular':
        raise ValueError('Legacy Project card requires migration: deskmate card migrate')
    owned = metadata is not None and metadata['provider'] is not None
    selected = (provider or default) if new or not owned else metadata['provider']
    detections = {p.key: providers.detect(p) for p in providers.PROVIDERS}
    choices = [p for p in installed if detections[p].compatible]
    result = dict(schema_version=1, status='ok', mode='new' if new or not owned else 'resume',
                  provider=selected, session_id=None if new or not owned else metadata['session_id'],
                  cwd=str(project), card_revision=metadata['revision'] if metadata else 0,
                  reason=None, warnings=[], choices=choices, possible_overlap=overlaps(journal))
    if selected not in choices:
        result.update(status='refused' if owned and not new else 'error',
                      reason='provider_unavailable', warnings=[detections[selected].reason])
    elif result['mode'] == 'resume' and not implementation(selected).resume_available(result['session_id'], str(project)):
        result.update(status='refused', reason='session_unavailable')
    return result


def confirm_ownership(card, legacy, journal, attempt):
    """Caller holds the project lock; confirming intent survives partial writes."""
    if attempt['state'] not in ('submitted', 'confirming') or not attempt['native_session_id']:
        return
    recovering = attempt['state'] == 'confirming'
    attempt['state'] = 'confirming'
    save_journal(card, journal)
    try:
        cards.claim_ownership_locked(card, legacy, attempt['expected_revision'], attempt['provider'],
                                     attempt['native_session_id'], recovering=recovering)
    except cards.RevisionConflict:
        attempt['state'] = 'conflict'
    else:
        attempt['state'] = 'confirmed'
    save_journal(card, journal)


def record_native_event(provider: str, payload: dict, launch_id: str | None) -> dict | None:
    if not isinstance(launch_id, str) or not LAUNCH_ID.fullmatch(launch_id):
        return None
    event, session, folder = (payload.get(key) for key in ('hook_event_name', 'session_id', 'cwd'))
    if (event not in ('SessionStart', 'SessionEnd', 'UserPromptSubmit')
            or not isinstance(session, str) or not NATIVE_ID.fullmatch(session)
            or not isinstance(folder, str) or not Path(folder).is_absolute()):
        return None
    try:
        _, _, card, legacy = cards.identity(folder)
    except (OSError, ValueError):
        return None
    # Unrelated native sessions must not create a project directory or lock.
    journal = read_journal(card)
    if not any(a['launch_id'] == launch_id for a in journal['attempts']):
        return None
    cards.read_card(card)
    with cards.locked(card):
        journal = read_journal(card)
        attempt = next((a for a in journal['attempts'] if a['launch_id'] == launch_id), None)
        if attempt is None or attempt['provider'] != provider:
            return None
        if attempt['requested_session_id'] is not None and attempt['requested_session_id'] != session:
            return None
        if attempt['native_session_id'] is not None and attempt['native_session_id'] != session:
            return None
        if event == 'SessionEnd':
            if attempt['native_session_id'] == session:
                attempt['ended'] = True
                save_journal(card, journal)
            return attempt
        if attempt['state'] in ('confirmed', 'failed', 'conflict') or attempt['ended']:
            return attempt
        attempt['native_session_id'] = session
        save_journal(card, journal)
        confirm_ownership(card, legacy, journal, attempt)
        return attempt


def start_session(plan: dict, *, title: str | None = None, prompt: str | None = None) -> dict:
    _, _, card, legacy = cards.identity(plan['cwd'])
    read_journal(card)  # Validate future schemas before creating lock/storage.
    cards.read_card(card)
    if cards.legacy_kind(legacy, card) == 'regular':
        raise ValueError('Legacy Project card requires migration')
    result = dict(plan)
    launch_id = uuid.uuid4().hex
    with cards.locked(card):
        journal = read_journal(card)
        _, metadata = cards.read_card(card)
        if (metadata['revision'] if metadata else 0) != plan['card_revision']:
            return {**result, 'status': 'conflict', 'reason': 'Project card changed before launch'}
        result['possible_overlap'] = overlaps(journal)
        attempt = dict(launch_id=launch_id, provider=plan['provider'], mode=plan['mode'],
                       expected_revision=plan['card_revision'], requested_session_id=plan['session_id'],
                       native_session_id=None, state='prepared', ended=False,
                       created_at=dt.datetime.now(dt.timezone.utc).isoformat())
        journal['attempts'].append(attempt)
        save_journal(card, journal)
    native = implementation(plan['provider']).launch(plan['cwd'], session_id=plan['session_id'],
                                                     title=title, prompt=prompt, launch_id=launch_id)
    with cards.locked(card):
        journal = read_journal(card)
        attempt = next(a for a in journal['attempts'] if a['launch_id'] == launch_id)
        if native.get('status') == 'error':
            attempt['state'] = 'failed'
            save_journal(card, journal)
            return {**result, 'status': 'error', 'reason': 'launch_failed',
                    'launch_id': launch_id, 'warnings': native.get('warnings', [])}
        attempt['state'] = 'submitted'
        save_journal(card, journal)
        confirm_ownership(card, legacy, journal, attempt)
        _, metadata = cards.read_card(card)
        result.update(launch_id=launch_id, status='confirmed' if attempt['state'] == 'confirmed' else
                      'conflict' if attempt['state'] == 'conflict' else 'pending',
                      reason='native_confirmation_pending' if attempt['state'] == 'submitted' else None,
                      session_id=attempt['native_session_id'] or plan['session_id'],
                      card_revision=metadata['revision'] if metadata else 0,
                      warnings=native.get('warnings', []))
    if result['status'] == 'pending':
        result['warnings'].append('Terminal command submitted; native hook confirmation is pending. Review hook trust if it remains pending.')
    return result


def render(result):
    provider = result.get('provider') or 'unknown Provider'
    if result['status'] == 'refused':
        return (f"Cannot resume {provider}: {result['reason']}. Ownership is unchanged.\n"
                'Choose an explicit new Work session with --new --provider ' +
                '|'.join(result.get('choices', [])) + '.\n')
    if result['status'] in ('error', 'invalid', 'conflict'):
        return 'Work session error: ' + str(result.get('reason')) + '\n'
    return (f"{result['mode']} Work session with {provider}: {result['cwd']} ({result['status']})\n" +
            ''.join(f'warning: {warning}\n' for warning in result.get('warnings', [])))


def exit_code(result):
    return {'refused': 4, 'conflict': 3, 'error': 1, 'invalid': 2}.get(result['status'], 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', required=True)
    parser.add_argument('--new', action='store_true')
    parser.add_argument('--provider', choices=('claude', 'codex'))
    parser.add_argument('--title')
    parser.add_argument('--prompt')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args()
    try:
        result = plan_session(args.folder, new=args.new, provider=args.provider)
        if not (args.dry_run or os.environ.get('DESKMATE_DRY_RUN')) and result['status'] == 'ok':
            result = start_session(result, title=args.title, prompt=args.prompt)
    except (OSError, ValueError, RuntimeError) as error:
        result = dict(schema_version=1, status='invalid', mode=None, provider=None,
                      session_id=None, card_revision=None, reason=str(error), warnings=[])
    print(json.dumps(result) if args.format == 'json' else render(result),
          end='\n' if args.format == 'json' else '')
    return exit_code(result)


if __name__ == '__main__':
    raise SystemExit(main())
