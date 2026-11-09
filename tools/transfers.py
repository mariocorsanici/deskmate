#!/usr/bin/env python3
"""Local redaction and private, one-use Provider transfer files."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_cards as cards

TTL = 3600
KIND = 'deskmate-provider-transfer'
NAME = re.compile(r'transfer-[A-Za-z0-9_-]+\.json')
KEY_BLOCK = re.compile(r'-----BEGIN ((?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY)-----.*?-----END \1-----', re.S)
ASSIGNMENT = re.compile(r'''(?P<prefix>(?<![\w])(?P<key>[A-Za-z_][A-Za-z0-9_.-]*)["'`*]*[ \t]*[:=][*]*[ \t]*)''')
TOKEN = re.compile(r'\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|hf_[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{12,}|AKIA[0-9A-Z]{16})\b')
BEARER = re.compile(r'(?i)\b(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}')
URL_PASSWORD = re.compile(r'(?i)(\b[a-z][a-z0-9+.-]*://[^\s:/]+:)([^@\s/]+)(@)')
def credential_key(name):
    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    parts = set(re.split(r'[^a-z0-9]+', name))
    return bool(parts & {'password', 'passwd', 'pass', 'secret', 'token',
                         'credential', 'credentials', 'authorization', 'apikey'}) or {'api', 'key'} <= parts


def redact(payload):
    counts = Counter()
    blocked = 0

    def replace(pattern, text, category, prefix=False):
        def replacement(match):
            counts[category] += 1
            return (match[1] if prefix else '') + '[REDACTED ' + category + ']'
        return pattern.sub(replacement, text)

    def assignments(text):
        nonlocal blocked
        pieces = []
        consumed = 0
        for match in ASSIGNMENT.finditer(text):
            if match.start() < consumed or not credential_key(match['key']):
                continue
            start = match.end()
            if start == len(text) or text[start] in '\r\n':
                continue
            end = start
            complete = True
            if text[start] in ('"', "'"):
                quote = text[start]
                end += 1
                complete = False
                while end < len(text) and text[end] not in '\r\n':
                    if text[end] == '\\':
                        end += 2
                    elif text[end] == quote:
                        end += 1
                        complete = True
                        break
                    else:
                        end += 1
                end = min(end, len(text))
            else:
                while end < len(text) and text[end] not in ' \t\r\n,;}':
                    end += 1
            pieces.append(text[consumed:start])
            if complete:
                counts['credential'] += 1
                pieces.append('[REDACTED credential]')
            else:
                blocked += 1
                pieces.append('[BLOCKED credential]')
            consumed = end
        return ''.join(pieces) + text[consumed:]

    def visit(value, key=''):
        nonlocal blocked
        if isinstance(value, dict):
            return {k: visit(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [visit(v) for v in value]
        if not isinstance(value, str):
            return value
        if credential_key(key) and value:
            counts['credential'] += 1
            return '[REDACTED credential]'
        text = replace(KEY_BLOCK, value, 'private-key')
        if re.search(r'-----BEGIN [^-\r\n]*PRIVATE KEY-----', text):
            blocked += 1
        text = assignments(text)
        text = replace(BEARER, text, 'bearer', prefix=True)
        text = replace(TOKEN, text, 'credential')
        def url_replacement(match):
            counts['credential'] += 1
            return match[1] + '[REDACTED credential]' + match[3]
        return URL_PASSWORD.sub(url_replacement, text)

    clean = visit(payload)
    return clean, dict(sorted(counts.items())), blocked


def manifest(body, redactions, blocked):
    delta = body.get('delta') or {}
    return {'source_provider': body['source_provider'], 'target_provider': body['target_provider'],
            'card_id': body['card_id'], 'card_revision': body['card_revision'],
            'bytes': len(json.dumps({**body, 'kind': KIND}).encode('utf-8')), 'redactions': redactions,
            'blocked_findings': blocked,
            'delta': {key: delta.get(key) for key in (
                'included_messages', 'omitted_messages', 'characters', 'omitted_characters', 'truncated', 'coverage')}}


def directory(create=False):
    path = cards.data_root() / 'transfers'
    if path.is_symlink():
        raise ValueError('Transfer directory must not be a symlink')
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() and (path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077):
        raise ValueError('Transfer directory must be owned by this user and private (0700)')
    return path


def create(body):
    parent = directory(create=True)
    fd, name = tempfile.mkstemp(prefix='transfer-', suffix='.json', dir=parent)
    path = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump({**body, 'kind': KIND}, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def inspect(path, *, provider=None, expired_ok=False):
    path = Path(path).absolute()
    path = path.parent.resolve() / path.name
    parent = directory()
    if path.parent != parent or not NAME.fullmatch(path.name):
        raise ValueError('Only managed transfer files can be read')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r', encoding='utf-8') as stream:
        metadata = os.fstat(stream.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_mode & 0o777 != 0o600 or metadata.st_nlink != 1):
            raise ValueError('Transfer file must be private, regular and owned by this user')
        body = json.load(stream)
    if (not isinstance(body, dict) or body.get('kind') != KIND
            or type(body.get('schema_version')) is not int or body['schema_version'] != 1
            or body.get('source_provider') not in ('claude', 'codex')
            or body.get('target_provider') not in ('claude', 'codex')
            or not isinstance(body.get('card_id'), str)):
        raise ValueError('Invalid managed transfer schema')
    if provider is not None and body['target_provider'] != provider:
        raise ValueError('Transfer belongs to a different target Provider')
    if not expired_ok and time.time() - metadata.st_mtime >= TTL:
        raise ValueError('Transfer expired; prepare a new preview and consent')
    return body, metadata


def consume(path, provider):
    path = Path(path).absolute()
    path = path.parent.resolve() / path.name
    body, metadata = inspect(path, provider=provider)
    # Refuse a replaced path rather than unlinking another file after reading.
    current = path.lstat()
    if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
        raise ValueError('Transfer changed while being read')
    path.unlink()
    return body


def cleanup():
    parent = directory()
    removed = 0
    if parent.exists():
        for path in parent.glob('transfer-*.json'):
            try:
                preliminary = path.lstat()
                if not stat.S_ISREG(preliminary.st_mode) or time.time() - preliminary.st_mtime < TTL:
                    continue
                _, metadata = inspect(path, expired_ok=True)
                current = path.lstat()
                if (time.time() - metadata.st_mtime >= TTL
                        and (current.st_dev, current.st_ino) == (metadata.st_dev, metadata.st_ino)):
                    path.unlink()
                    removed += 1
            except (OSError, ValueError, UnicodeError):
                continue
    return {'schema_version': 1, 'status': 'ok', 'removed': removed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['read', 'cleanup'])
    parser.add_argument('--bundle')
    parser.add_argument('--provider', choices=['claude', 'codex'])
    args = parser.parse_args()
    try:
        if args.operation == 'read':
            if not args.bundle or not args.provider:
                raise ValueError('Bundle path and target Provider are required')
            result = consume(args.bundle, args.provider)
        else:
            result = cleanup()
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, UnicodeError):
        # Decoder errors can contain fragments of the private bundle; never echo them.
        print(json.dumps({'schema_version': 1, 'status': 'invalid',
                          'reason': 'Transfer unavailable, invalid, expired or owned by another Provider'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
