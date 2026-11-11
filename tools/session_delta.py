#!/usr/bin/env python3
"""Bounded, provider-neutral Session delta extraction (read-only)."""
from __future__ import annotations

import argparse
from collections import deque
import importlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_cards
import providers
from checkpoints import checkpoint_boundary, instant

DEFAULT_MESSAGES = 12
DEFAULT_CHARACTERS = 6000


def positive(value):
    if type(value) is not int or value < 1:
        raise ValueError('Session delta limits must be positive integers')
    return value


def configured_limits(max_messages=None, max_characters=None):
    config = providers.read_config()
    section = config.get('session_delta', {})
    if not isinstance(section, dict):
        raise ValueError('session_delta must be a configuration object')
    messages = positive(section.get('max_messages', DEFAULT_MESSAGES))
    characters = positive(section.get('max_characters', DEFAULT_CHARACTERS))
    return (messages if max_messages is None else positive(max_messages),
            characters if max_characters is None else positive(max_characters))


def saved_checkpoint(folder, provider, session_id):
    """Use durable matching ownership, never a possibly cancelled skill prompt."""
    if not folder:
        return None
    _, _, card, _ = project_cards.identity(folder)
    text, metadata = project_cards.read_card(card)
    if (not metadata or metadata['provider'] != provider
            or metadata['session_id'] != session_id):
        return None
    return checkpoint_boundary(text, session_id=session_id)


def is_conversation(message):
    if message['role'] != 'user':
        return True
    # Native runtimes store these injected instructions as user messages.
    text = message['text'].lstrip()
    return not text.startswith(('<environment_context>', '<user_instructions>',
                                '<permissions instructions>', '<collaboration_mode>',
                                '<skill>', '# AGENTS.md instructions'))


class Selection:
    """Keep only bounded early/recent candidates while counting all eligible text."""
    def __init__(self, provider, session_id, max_messages, max_characters, after):
        self.provider = provider
        self.session_id = session_id
        self.max_messages = positive(max_messages)
        self.max_characters = positive(max_characters)
        self.checkpoint = ({'timestamp': instant(after, require_zone=True).isoformat(),
                            'source': 'explicit', 'precision': 'second'} if after is not None else None)
        self.resolved = after is not None
        self.replay_required = False
        self.head = None
        self.tail = deque(maxlen=max(1, max_messages - 1))
        self.total_messages = 0
        self.total_characters = 0
        self.warnings = []

    def warn(self, warning):
        if warning not in self.warnings:
            self.warnings.append(warning)

    def add(self, message, session):
        if session.get('id') != self.session_id:
            self.warn('Transcript identity does not match the requested Work session; messages were omitted.')
            return
        if not self.resolved and session.get('cwd'):
            self.resolved = True
            try:
                self.checkpoint = saved_checkpoint(session['cwd'], self.provider, self.session_id)
            except (OSError, UnicodeError, ValueError):
                self.warn('Saved Checkpoint is unreadable or invalid; coverage starts at session start.')
            # A rare late project identity needs a second streaming pass, so
            # early candidates and all counts respect the newly known boundary.
            self.replay_required = bool(self.checkpoint and self.total_messages)
            if self.checkpoint and self.checkpoint['precision'] == 'minute':
                self.warn('Saved Checkpoint has minute precision and assumes the local timezone; boundary is estimated.')
        if not is_conversation(message):
            return
        try:
            message['text'].encode('utf-8', errors='strict')
        except UnicodeError:
            self.warn('Malformed Unicode conversation text was omitted.')
            return
        try:
            stamp = instant(message['timestamp'], native=True)
        except ValueError:
            stamp = None
            self.warn('Conversation timestamps are unknown or invalid; coverage is incomplete.')
        if self.checkpoint:
            if stamp is None:
                return
            if stamp <= instant(self.checkpoint['timestamp']):
                return
        message = {**message, 'timestamp': stamp.isoformat() if stamp else None}
        self.total_messages += 1
        self.total_characters += len(message['text'])
        bounded = {**message, 'text': message['text'][:self.max_characters]}
        if self.head is None:
            self.head = bounded
        else:
            self.tail.append(bounded)

    def messages(self):
        if self.head is None:
            return []
        if self.max_messages == 1:
            return [self.tail[-1] if self.tail else self.head]
        candidates = [self.head, *self.tail]
        budget = self.max_characters
        if sum(len(message['text']) for message in candidates) <= budget:
            return candidates
        if budget == 1 or len(candidates) == 1:
            return [{**candidates[-1], 'text': candidates[-1]['text'][:budget]}]
        early = {**candidates[0], 'text': candidates[0]['text'][:budget // 2]}
        remaining = budget - len(early['text'])
        recent = []
        for message in reversed(candidates[1:]):
            if not remaining:
                break
            clipped = {**message, 'text': message['text'][:remaining]}
            recent.append(clipped)
            remaining -= len(clipped['text'])
        return [early, *reversed(recent)]

    def result(self, session):
        messages = self.messages()
        characters = sum(len(message['text']) for message in messages)
        omitted_messages = self.total_messages - len(messages)
        omitted_characters = self.total_characters - characters
        truncated = bool(omitted_messages or omitted_characters)
        warnings = list(dict.fromkeys([*session.get('warnings', []), *self.warnings]))
        degraded = session.get('status') == 'degraded' or bool(self.warnings)
        coverage = 'partial' if truncated or degraded else 'full'
        if degraded and not self.total_messages:
            coverage = 'unavailable'
        return {'schema_version': 1, 'provider': self.provider, 'id': self.session_id,
                'status': 'degraded' if degraded else 'ok', 'warnings': warnings,
                'checkpoint': self.checkpoint, 'messages': messages,
                'limits': {'max_messages': self.max_messages, 'max_characters': self.max_characters},
                'included_messages': len(messages), 'omitted_messages': omitted_messages,
                'characters': characters, 'omitted_characters': omitted_characters,
                'truncated': truncated,
                'coverage': {'origin': 'checkpoint' if self.checkpoint else 'session-start',
                             'status': coverage,
                             'counts': 'readable conversation messages only; corrupt records are not counted'}}


def extract(provider, session_id, reader, *, max_messages=DEFAULT_MESSAGES,
            max_characters=DEFAULT_CHARACTERS, after=None):
    selection = Selection(provider, session_id, max_messages, max_characters, after)
    session = reader(session_id, on_message=selection.add)
    if selection.replay_required:
        replay = Selection(provider, session_id, max_messages, max_characters, after)
        replay.checkpoint = selection.checkpoint
        replay.resolved = True
        replay.warnings = selection.warnings[:]
        session = reader(session_id, on_message=replay.add)
        selection = replay
    return selection.result(session)


def render(result):
    limits = result['limits']
    lines = [f"Session delta: {result['provider']} {result['id']} ({result['status']})",
             f"Coverage: {result['coverage']['status']} from {result['coverage']['origin']}",
             f"Messages: {result['included_messages']} included, {result['omitted_messages']} omitted; "
             f"characters: {result['characters']} included, {result['omitted_characters']} omitted",
             f"Limits: {limits['max_messages']} messages, {limits['max_characters']} characters; "
             f"truncated: {str(result['truncated']).lower()}"]
    for message in result['messages']:
        lines.append(f"[{message['timestamp'] or 'unknown time'}] {message['role']}: {message['text']}")
    lines.extend('warning: ' + warning for warning in result['warnings'])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['claude', 'codex'], required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--after')
    parser.add_argument('--max-messages', type=int)
    parser.add_argument('--max-characters', type=int)
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    args = parser.parse_args()
    try:
        max_messages, max_characters = configured_limits(args.max_messages, args.max_characters)
        adapter = importlib.import_module('adapter_' + args.provider)
        result = adapter.read_delta(args.session_id, max_messages=max_messages,
                                    max_characters=max_characters, after=args.after)
        print(json.dumps(result) if args.format == 'json' else render(result))
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
