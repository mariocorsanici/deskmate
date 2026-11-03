#!/usr/bin/env python3
"""Consume native Provider hook JSON and record Deskmate activity."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activity_log

SKILLS = {'whats-on-today', 'how-did-it-go', 'call-it-a-day', 'study-later', 'checkpoint'}


def handle(provider, payload):
    event = payload.get('hook_event_name', '')
    session = payload.get('session_id', '')
    cwd = payload.get('cwd', '')
    if not isinstance(session, str) or not isinstance(cwd, str):
        raise ValueError('session_id and cwd must be strings')
    name, detail = '', ''
    if event == 'PreToolUse' and provider == 'claude' and payload.get('tool_name') == 'Skill':
        tool = payload.get('tool_input') or {}
        if not isinstance(tool, dict):
            raise ValueError('tool_input must be an object')
        name, detail = tool.get('skill', ''), tool.get('args', '')
    elif event == 'UserPromptSubmit':
        prompt = payload.get('prompt', '')
        if not isinstance(prompt, str):
            raise ValueError('prompt must be a string')
        prefix = '/' if provider == 'claude' else '$'
        matched = re.fullmatch(r'\s*' + re.escape(prefix) + r'([a-z-]+)(?:\s+(.*))?', prompt, re.DOTALL)
        if matched:
            name, detail = matched.group(1), matched.group(2) or ''
    if event == 'Stop' and session:
        import metrics
        metrics.usage_records(provider)
        if provider == 'claude':
            import token_usage
            if token_usage.update_usage(session):
                raise ValueError('Claude usage update failed')
        metrics.update_session_usage(provider, session)
        return
    if name in SKILLS:
        if not isinstance(detail, str):
            raise ValueError('skill arguments must be a string')
        activity_log.append_event(name, detail, session, cwd, provider)
    elif event in ('SessionStart', 'SessionEnd'):
        activity_log.append_event('session-start' if event == 'SessionStart' else 'session-end',
                                  '', session, cwd, provider)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', required=True, choices=activity_log.PROVIDERS)
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('hook payload must be an object')
        handle(args.provider, payload)
        # Codex hooks require native JSON rather than human-readable output.
        print('{}')
        return 0
    except (ValueError, OSError, csv.Error) as error:
        print(f'hook event: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
