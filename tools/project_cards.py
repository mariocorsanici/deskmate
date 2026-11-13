#!/usr/bin/env python3
"""Shared Markdown Project cards, revision-checked writes and Claude migration."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checkpoints import checkpoint_boundary
from provider_environment import claude_home

ROOT = Path(__file__).resolve().parents[1]


def data_root() -> Path:
    return Path(os.environ.get('DESKMATE_DATA_DIR', str(ROOT / 'data'))).expanduser().resolve()


def identity(folder: str) -> tuple[Path, str, Path, Path]:
    project = Path(folder).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError('project must be an existing directory')
    slug = re.sub(r'[^a-z0-9]+', '-', project.name.lower()).strip('-') or 'project'
    key = slug + '-' + hashlib.sha256(str(project).encode()).hexdigest()[:12]
    card = data_root() / 'projects' / key / 'project-card.md'
    legacy_key = re.sub(r'[^a-zA-Z0-9]', '-', str(project))
    legacy = claude_home() / 'projects' / legacy_key / 'memory/project-card.md'
    return project, key, card, legacy


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate metadata key: {key}')
        result[key] = value
    return result


def validate(metadata):
    fields = {'schema_version', 'revision', 'provider', 'session_id'}
    if not isinstance(metadata, dict) or set(metadata) != fields:
        raise ValueError('invalid Deskmate metadata fields')
    if type(metadata['schema_version']) is not int or metadata['schema_version'] != 1:
        raise ValueError('unsupported schema_version; expected 1')
    if type(metadata['revision']) is not int or metadata['revision'] < 1:
        raise ValueError('revision must be a positive integer')
    provider, session = metadata['provider'], metadata['session_id']
    if provider is None and session is None:
        return metadata
    if provider not in ('claude', 'codex') or not isinstance(session, str) or not session.strip():
        raise ValueError('provider and non-empty session_id must be set together')
    return metadata


def parse(text: str):
    """Return frontmatter (without owned metadata), body, and validated metadata."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip('\r\n') != '---':
        return None, text, None
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip('\r\n') == '---'), None)
    if end is None:
        raise ValueError('unterminated frontmatter')
    header, metadata = [], None
    seen = False
    for line in lines[1:end]:
        if re.match(r'^\s*deskmate\s*:', line):
            if seen:
                raise ValueError('duplicate deskmate metadata')
            seen = True
            metadata = validate(json.loads(line.split(':', 1)[1], object_pairs_hook=unique_object))
        else:
            header.append(line)
    return ''.join(header), ''.join(lines[end + 1:]), metadata


def render(text: str, metadata: dict) -> str:
    header, body, _ = parse(text)
    return '---\n' + (header or '') + 'deskmate: ' + json.dumps(metadata, sort_keys=True, separators=(',', ':')) + '\n---\n' + body


def without_metadata(text: str):
    header, body, _ = parse(text)
    return (header or '', body)


def read_card(card: Path):
    if card.is_symlink():
        raise ValueError('shared card must be a regular file, not a symlink')
    if not card.exists():
        return None, None
    text = card.read_bytes().decode('utf-8')
    metadata = parse(text)[2]
    if metadata is None:
        raise ValueError('shared card is missing Deskmate metadata')
    return text, metadata


@contextmanager
def locked(card: Path):
    card.parent.mkdir(parents=True, exist_ok=True)
    with (card.parent / '.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def atomic_write(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.card-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.lexists(name):
            os.unlink(name)


def legacy_kind(legacy: Path, card: Path) -> str:
    if legacy.is_symlink():
        if legacy.resolve() != card:
            raise ValueError(f'unexpected legacy symlink: {legacy}')
        return 'linked'
    if not legacy.exists():
        return 'missing'
    if not legacy.is_file():
        raise ValueError(f'legacy card must be a regular file: {legacy}')
    return 'regular'


def ensure_link(legacy: Path, card: Path, replace_regular=False):
    kind = legacy_kind(legacy, card)
    if kind == 'linked':
        return
    if kind == 'regular' and not replace_regular:
        raise ValueError('legacy card requires migration; run deskmate card migrate')
    legacy.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.card-link-', dir=legacy.parent)
    os.close(fd)
    os.unlink(name)
    try:
        os.symlink(str(card), name)
        os.replace(name, legacy)
    finally:
        if os.path.lexists(name):
            os.unlink(name)


def locate(card: Path, legacy: Path):
    _, metadata = read_card(card)
    if metadata is not None:
        with locked(card):
            _, metadata = read_card(card)
            # Leave a legacy regular file for explicit migration/conflict resolution.
            if legacy_kind(legacy, card) != 'regular':
                ensure_link(legacy, card)
    print(json.dumps({'path': str(card), 'metadata': metadata}, sort_keys=True))


def write(card: Path, legacy: Path, args) -> int:
    if args.expected_revision < 0 or not args.session_id.strip():
        raise ValueError('expected revision must be nonnegative and session ID non-empty')
    candidate = Path(args.source).expanduser().read_bytes().decode('utf-8')
    parse(candidate)  # Validate before creating storage, including future metadata.
    checkpoint_boundary(candidate)
    read_card(card)
    if legacy_kind(legacy, card) == 'regular':
        raise ValueError('legacy card requires migration; run deskmate card migrate')
    with locked(card):
        current, metadata = read_card(card)
        revision = metadata['revision'] if metadata else 0
        if revision != args.expected_revision:
            sys.stdout.write(current or '')
            print(f'revision conflict: current revision is {revision}', file=sys.stderr)
            return 3
        if legacy_kind(legacy, card) == 'regular':
            raise ValueError('legacy card requires migration')
        metadata = dict(schema_version=1, revision=revision + 1, provider=args.provider, session_id=args.session_id)
        atomic_write(card, render(candidate, metadata).encode('utf-8'))
        ensure_link(legacy, card)
    print(json.dumps({'path': str(card), 'metadata': metadata}, sort_keys=True))
    return 0


class RevisionConflict(ValueError):
    """A pending launch cannot replace a newer Project card."""


def claim_ownership_locked(card: Path, legacy: Path, expected_revision: int,
                           provider: str, session_id: str, *, recovering=False):
    """Update ownership only. The caller must hold this project's card lock."""
    current, metadata = read_card(card)
    revision = metadata['revision'] if metadata else 0
    # A durable confirming journal entry permits retry after card publication.
    if (recovering and metadata and revision == expected_revision + 1
            and metadata['provider'] == provider and metadata['session_id'] == session_id):
        ensure_link(legacy, card)
        return metadata
    if revision != expected_revision:
        raise RevisionConflict(f'revision conflict: current revision is {revision}')
    replacement = dict(schema_version=1, revision=revision + 1, provider=provider, session_id=session_id)
    validate(replacement)
    if legacy_kind(legacy, card) == 'regular':
        raise ValueError('Legacy Project card requires migration')
    if current is None:
        current = '# Project card\n\n## Status\nWork session started; no Checkpoint recorded yet.\n\n## Checks\n'
    atomic_write(card, render(current, replacement).encode('utf-8'))
    ensure_link(legacy, card)
    return replacement


def backup(raw: bytes, key: str):
    path = data_root() / 'backups/project-cards' / key / (hashlib.sha256(raw).hexdigest() + '.md')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic publication prevents a crash leaving a truncated content-addressed backup.
    fd, name = tempfile.mkstemp(prefix='.backup-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(name, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != raw:
                raise ValueError('existing backup does not match its content hash')
    finally:
        os.unlink(name)


def migrate(card: Path, legacy: Path, key: str):
    read_card(card)  # Reject unsupported stored schema before any mutation.
    kind = legacy_kind(legacy, card)
    if kind == 'regular':
        parse(legacy.read_bytes().decode('utf-8'))
    if kind == 'missing' and not card.exists():
        print('no legacy card; nothing to migrate')
        return
    with locked(card):
        current, metadata = read_card(card)
        kind = legacy_kind(legacy, card)
        if kind == 'regular':
            raw = legacy.read_bytes()
            text = raw.decode('utf-8')
            parse(text)
            backup(raw, key)
            if current is not None:
                if without_metadata(current) != without_metadata(text):
                    raise ValueError('migration conflict: shared and legacy cards differ; backup preserved')
            else:
                checkpoints = re.findall(r'^Checkpoint[^\r\n]*', text, re.M)
                match = re.search(r'\bsession `([^`]+)`', checkpoints[-1]) if checkpoints else None
                session = match.group(1) if match and match.group(1).strip() else None
                metadata = dict(schema_version=1, revision=1, provider='claude' if session else None, session_id=session)
                atomic_write(card, render(text, metadata).encode('utf-8'))
            ensure_link(legacy, card, replace_regular=True)
        elif current is not None:
            ensure_link(legacy, card)
        elif kind == 'linked':
            raise ValueError('legacy link has no shared card to recover')
    print(f'migrated: {card}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    commands.add_parser('list')
    for name in ('locate', 'migrate', 'write'):
        sub = commands.add_parser(name)
        sub.add_argument('project')
        if name == 'write':
            sub.add_argument('--expected-revision', type=int, required=True)
            sub.add_argument('--provider', choices=('claude', 'codex'), required=True)
            sub.add_argument('--session-id', required=True)
            sub.add_argument('--from', dest='source', required=True)
    args = parser.parse_args()
    try:
        if args.operation == 'list':
            cards = sorted((data_root() / 'projects').glob('*/project-card.md'))
            for card in cards:
                read_card(card)
            for card in cards:
                print(card)
            return 0
        _, key, card, legacy = identity(args.project)
        if args.operation == 'locate':
            locate(card, legacy)
        elif args.operation == 'write':
            return write(card, legacy, args)
        else:
            migrate(card, legacy, key)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f'card: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
