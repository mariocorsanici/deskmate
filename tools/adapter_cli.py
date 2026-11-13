#!/usr/bin/env python3
"""Shared command facade for Provider adapters."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import pathlib
import shlex
import sys
import csv
import os
import subprocess
import tempfile

# Executed with -I: only the repository's own adapter directory is added.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))


def adapter(provider):
    return importlib.import_module('adapter_' + provider)


def print_sessions(records, count, cut):
    for session in records:
        print('=' * 80)
        print(f"SESSION {session['id']}")
        print(f"provider: {session['provider']}")
        print(f"folder:  {session['cwd']}")
        print(f"active:  {session['start']} -> {session['end']}")
        if session['cwd']:
            import project_cards
            try:
                _, _, card, _ = project_cards.identity(session['cwd'])
                _, owner = project_cards.read_card(card)
            except (OSError, ValueError):
                owner = None
            if owner and (owner['provider'], owner['session_id']) == (session['provider'], session['id']):
                print(f"resume:  {shlex.join(['deskmate', 'work-session', '--folder', session['cwd']])}")
            else:
                print(f"resume unresolved: {session['provider']}:{session['id']}; "
                      "write a Checkpoint in that Work session before routing this Project.")
        for message in session.get('messages', [])[-count:] if count else []:
            who = 'USER' if message['role'] == 'user' else session['provider'].upper()
            text = message['text']
            if len(text) > cut:
                text = text[:cut] + ' […]'
            print(f"[{message['timestamp']}] {who}: {text}\n")
        if 'coverage' in session:
            print('delta: ' + json.dumps({key: session[key] for key in (
                'checkpoint', 'limits', 'included_messages', 'omitted_messages', 'characters',
                'omitted_characters', 'truncated', 'coverage')}))
        for warning in session.get('warnings', []):
            print(f'warning: {warning}')


def verify_logging(provider):
    """Run the installed prompt hook in disposable state and inspect its event."""
    with tempfile.TemporaryDirectory(prefix='deskmate-hook-verification-') as directory:
        home = pathlib.Path(directory)
        data = home / 'data'
        native = 'deskmate-integration-verification'
        command, payload = adapter(provider).verification_hook(native, directory)
        environment = {**os.environ, 'HOME': directory, 'DESKMATE_DATA_DIR': str(data),
                       'CODEX_HOME': str(home / '.codex'),
                       'CLAUDE_CONFIG_DIR': str(home / '.claude')}
        checked = subprocess.run([sys.executable, *command], input=json.dumps(payload),
                                 capture_output=True, text=True, env=environment,
                                 cwd=directory, timeout=10, check=False)
        if checked.returncode:
            raise ValueError('Synthetic hook logging failed: ' + checked.stderr.strip())
        with (data / 'log.csv').open(encoding='utf-8', newline='') as handle:
            records = list(csv.DictReader(handle))
        if not any(row.get('provider') == provider and row.get('session') == native
                   and row.get('event') == 'checkpoint' for row in records):
            raise ValueError('Synthetic hook produced no matching Provider activity event.')
    return {'status': 'ok', 'provider': provider, 'event': 'checkpoint',
            'scope': 'isolated synthetic hook; native runtime approval remains manual'}


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    sessions = commands.add_parser('sessions')
    sessions.add_argument('--provider', choices=['claude', 'codex', 'all'], default='all')
    sessions.add_argument('--since', default=dt.date.today().isoformat())
    sessions.add_argument('--messages', type=int, default=0)
    sessions.add_argument('--cut', type=int, default=700)
    sessions.add_argument('--format', choices=['text', 'json'], default='text')
    session = commands.add_parser('session')
    session.add_argument('--provider', choices=['claude', 'codex'], required=True)
    session.add_argument('--session-id', required=True)
    session.add_argument('--usage-only', action='store_true')
    launch = commands.add_parser('provider-launch')
    launch.add_argument('--provider', choices=['claude', 'codex'], required=True)
    launch.add_argument('--folder', required=True)
    launch.add_argument('--session-id')
    launch.add_argument('--prompt')
    launch.add_argument('--title')
    launch.add_argument('--dry-run', action='store_true')
    integration = commands.add_parser('integration')
    integration.add_argument('--provider', choices=['claude', 'codex'], required=True)
    integration.add_argument('--remove', action='store_true')
    integration.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'integration':
            if args.remove and args.verify:
                raise ValueError('--remove and --verify cannot be combined')
            result = adapter(args.provider).configure_hooks(remove=args.remove)
            if args.verify and result.get('status') != 'error':
                try:
                    result['verification'] = verify_logging(args.provider)
                except (OSError, ValueError, subprocess.SubprocessError, csv.Error) as error:
                    result['verification'] = {'status': 'error', 'provider': args.provider}
                    result['status'] = 'error'
                    result.setdefault('warnings', []).append(str(error))
            print(json.dumps(result))
            return 1 if result.get('status') == 'error' else 0
        if args.command == 'provider-launch':
            result = adapter(args.provider).launch(args.folder, session_id=args.session_id,
                                                   prompt=args.prompt, title=args.title,
                                                   dry_run=args.dry_run)
            print(json.dumps(result))
            return 1 if result.get('status') == 'error' else 0
        if args.command == 'session':
            implementation = adapter(args.provider)
            reader = implementation.read_usage if args.usage_only else implementation.read_session
            print(json.dumps(reader(args.session_id)))
            return 0
        dt.date.fromisoformat(args.since)
        if args.messages < 0 or args.cut < 0:
            raise ValueError('message and character limits must be nonnegative')
        providers = ['claude', 'codex'] if args.provider == 'all' else [args.provider]
        records = []
        for provider in providers:
            implementation = adapter(provider)
            discovered = implementation.discover(args.since)
            if args.messages:
                if args.cut == 0:
                    raise ValueError('--cut must be positive when reading messages')
                from session_delta import configured_limits
                configured_limits(args.messages, args.cut)
                discovered = [{**item, **implementation.read_delta(item['id'], max_messages=args.messages,
                                                        max_characters=args.cut)}
                              for item in discovered]
            records.extend(discovered)
        if args.format == 'json':
            print(json.dumps(records))
        else:
            print_sessions(records, args.messages, args.cut)
        return 0
    except (OSError, ValueError, ImportError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
