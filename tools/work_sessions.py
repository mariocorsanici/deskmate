#!/usr/bin/env python3
"""Route Project continuation and retain evidence of native Work session launch."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_cards as cards
import providers


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
    if cards.legacy_kind(legacy, card) == 'regular':
        raise ValueError('Legacy Project card requires migration: deskmate card migrate')
    owned = metadata is not None and metadata['provider'] is not None
    selected = (provider or default) if new or not owned else metadata['provider']
    detections = {p.key: providers.detect(p) for p in providers.PROVIDERS}
    choices = [p for p in installed if detections[p].compatible]
    result = dict(schema_version=1, status='ok', mode='new' if new or not owned else 'resume',
                  provider=selected, session_id=None if new or not owned else metadata['session_id'],
                  cwd=str(project), card_revision=metadata['revision'] if metadata else 0,
                  reason=None, warnings=[], choices=choices)
    if selected not in choices:
        result.update(status='refused' if owned and not new else 'error',
                      reason='provider_unavailable', warnings=[detections[selected].reason])
    elif result['mode'] == 'resume' and not implementation(selected).resume_available(result['session_id'], str(project)):
        result.update(status='refused', reason='session_unavailable')
    return result


def render(result):
    provider = result.get('provider') or 'unknown Provider'
    if result['status'] == 'refused':
        return (f"Cannot resume {provider}: {result['reason']}. Ownership is unchanged.\n"
                'Choose an explicit new Work session with --new --provider ' +
                '|'.join(result.get('choices', [])) + '.\n')
    if result['status'] == 'error':
        return 'Work session error: ' + str(result.get('reason')) + '\n'
    return f"{result['mode']} Work session with {provider}: {result['cwd']} ({result['status']})\n"


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
        if not args.dry_run and result['status'] == 'ok':
            result.update(status='error', reason='Launch submission is not implemented yet')
    except (OSError, ValueError, RuntimeError) as error:
        result = dict(schema_version=1, status='invalid', mode=None, provider=None,
                      session_id=None, card_revision=None, reason=str(error), warnings=[])
    print(json.dumps(result) if args.format == 'json' else render(result),
          end='\n' if args.format == 'json' else '')
    return exit_code(result)


if __name__ == '__main__':
    raise SystemExit(main())
