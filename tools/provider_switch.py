#!/usr/bin/env python3
"""Explicit new-Provider continuation from durable state and current Checks."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check
import project_cards as cards
import work_sessions

ROOT = Path(__file__).resolve().parents[1]


def prepare(folder, target):
    project, key, card, _ = cards.identity(folder)
    text, owner = cards.read_card(card)
    if not owner or owner['provider'] is None:
        raise ValueError('A Provider switch requires a Project card with recorded ownership')
    if owner['provider'] == target:
        raise ValueError('Target is the recorded Provider; use work-session to resume it')
    plan = work_sessions.plan_session(str(project), new=True, provider=target)
    plan.update(source_provider=owner['provider'], source_session_id=owner['session_id'],
                card_id=key, coverage='card-and-checks')
    journal = work_sessions.read_journal(card)
    source_attempts = [a for a in journal['attempts'] if a['provider'] == owner['provider']
                       and a['native_session_id'] == owner['session_id']]
    if not source_attempts or any(not a['ended'] for a in source_attempts):
        plan['possible_overlap'].append({'provider': owner['provider'],
                                         'native_session_id': owner['session_id'], 'state': 'unknown'})
    warnings = ['Transcript context is unavailable in this card-and-Checks transfer; ask only for missing context.']
    results = []
    if plan['status'] == 'ok':
        for line in check.section(text, 'Checks').splitlines():
            matched = check.CHECK.match(line)
            if matched:
                state, output = check.run(matched[2])
                results.append({'label': matched[1], 'status': state, 'output': output[:1000]})
                if state != 'ok':
                    warnings.append('Some current Checks are unavailable; treat those facts as unknown.')
    plan['warnings'] = list(dict.fromkeys([*plan['warnings'], *warnings]))
    body = {'schema_version': 1, 'source_provider': owner['provider'], 'target_provider': target,
            'card_id': key, 'card_revision': owner['revision'], 'card': text, 'checks': results,
            'instructions': 'Continue from the Project card and current Checks. Ask only for missing context.',
            'warnings': warnings}
    plan['checks_count'] = len(results)
    return plan, body


def private_bundle(body):
    directory = cards.data_root() / 'transfers'
    if directory.is_symlink():
        raise ValueError('Transfer directory must not be a symlink')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_mode & 0o077:
        raise ValueError('Transfer directory must have private permissions (0700)')
    fd, path = tempfile.mkstemp(prefix='transfer-', suffix='.json', dir=directory)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(body, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return Path(path)


def launch(plan, body):
    _, _, card, _ = cards.identity(plan['cwd'])
    current, owner = cards.read_card(card)
    if not owner or owner['revision'] != plan['card_revision'] or current != body['card']:
        return {**plan, 'status': 'conflict', 'reason': 'Project card changed after preview'}
    path = private_bundle(body)
    prompt = (f'Read the private Deskmate transfer at {path}. '
              'Continue this Project from its saved card and current Checks; ask only for missing context.')
    result = work_sessions.start_session(plan, prompt=prompt)
    if result['status'] == 'conflict' or (result['status'] == 'error' and result.get('reason') != 'launch_uncertain'):
        path.unlink(missing_ok=True)
    return result


def show(plan):
    print(f"Provider switch: {plan.get('source_provider')} -> {plan.get('provider')}")
    print(f"Project card: {plan.get('card_id')}, revision {plan.get('card_revision')}; current Checks: {plan.get('checks_count', 0)}")
    if plan.get('possible_overlap'):
        print('Warning: potentially simultaneous Work sessions may still be active.')
    for warning in plan.get('warnings', []):
        print('warning: ' + warning)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', required=True)
    parser.add_argument('--to', choices=['claude', 'codex'], required=True)
    parser.add_argument('--preview', '--dry-run', action='store_true')
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    args = parser.parse_args()
    try:
        plan, body = prepare(args.folder, args.to)
        if plan['status'] == 'ok' and not args.preview:
            if args.format == 'json' or not (sys.stdin.isatty() and sys.stdout.isatty()):
                plan.update(status='refused', reason='interactive_consent_required')
            else:
                show(plan)
                if input('Confirm transfer and start a NEW target Work session? Type yes: ').strip() != 'yes':
                    plan.update(status='cancelled', reason='User cancelled; ownership unchanged')
                else:
                    plan = launch(plan, body)
    except (OSError, ValueError, EOFError, RuntimeError) as error:
        plan = {'schema_version': 1, 'status': 'invalid', 'reason': str(error), 'warnings': []}
    if args.format == 'json':
        print(json.dumps(plan))
    else:
        show(plan)
        print('Switch ' + plan['status'] + ': ' + str(plan.get('reason') or ''))
    return work_sessions.exit_code(plan)


if __name__ == '__main__':
    raise SystemExit(main())
