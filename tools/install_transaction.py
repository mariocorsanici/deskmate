"""Recoverable, compare-before-replace publication of an installation plan."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import uuid


def state(path):
    if path.is_symlink():
        return {'kind': 'link', 'target': os.readlink(path)}
    if not path.exists():
        return {'kind': 'missing'}
    if not path.is_file():
        raise ValueError(f'Expected a regular file or owned link: {path}')
    return {'kind': 'file', 'mode': stat.S_IMODE(path.stat().st_mode),
            'content': path.read_bytes()}


def file_state(content, mode=0o600):
    return {'kind': 'file', 'content': content, 'mode': mode}


def replace(path, value):
    """Atomic replacement on the destination filesystem; never follow a link."""
    if value['kind'] == 'missing':
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.deskmate-', dir=path.parent)
    try:
        if value['kind'] == 'link':
            os.close(fd)
            os.unlink(name)
            os.symlink(value['target'], name)
        else:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(value['content'])
                handle.flush()
                os.fchmod(handle.fileno(), value['mode'])
                os.fsync(handle.fileno())
        os.replace(name, path)
        # Make the directory entry durable as well as its file contents.
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.lexists(name):
            os.unlink(name)


class Transaction:
    def __init__(self, data):
        self.data = data
        self.entries = []
        self.directory = None
        self.metadata = {}

    def add(self, path, after, before=None):
        path = Path(path)
        before = state(path) if before is None else before
        if before != after:
            self.entries.append({'path': path, 'before': before, 'after': after})

    def encode(self, value):
        result = dict(value)
        if result['kind'] == 'file':
            raw = result.pop('content')
            digest = hashlib.sha256(raw).hexdigest()
            result['blob'] = digest
            target = self.directory / digest
            if not target.exists():
                replace(target, file_state(raw))
        return result

    def save(self, status):
        record = {'schema_version': 1, 'status': status, 'metadata': self.metadata, 'entries': [
            {'path': str(entry['path']), 'before': self.encode(entry['before']),
             'after': self.encode(entry['after'])} for entry in self.entries]}
        replace(self.directory / 'transaction.json',
                file_state((json.dumps(record, indent=2) + '\n').encode()))

    def apply(self):
        if not self.entries and not any(self.metadata.values()):
            return
        for entry in self.entries:
            if state(entry['path']) != entry['before']:
                raise ValueError(f'Changed during setup; retry after other writers finish: {entry["path"]}')
        self.directory = self.data / 'backups/install' / uuid.uuid4().hex
        self.directory.mkdir(parents=True, mode=0o700)
        self.save('pending')
        try:
            for entry in self.entries:
                if state(entry['path']) != entry['before']:
                    raise ValueError(f'Changed during setup: {entry["path"]}')
                replace(entry['path'], entry['after'])
        except BaseException:
            self.rollback()
            raise

    def rollback(self, restore=None):
        if self.directory is None:
            return
        # Refuse all restoration if any file now belongs to a concurrent writer.
        for entry in self.entries:
            if state(entry['path']) not in (entry['before'], entry['after']):
                raise ValueError(f'Cannot recover changed file {entry["path"]}; '
                                 f'preserved backups in {self.directory}')
        for entry in reversed(self.entries):
            if state(entry['path']) == entry['after']:
                replace(entry['path'], entry['before'])
        if restore is not None:
            restore(self.metadata)
        self.save('rolled-back')

    def commit(self):
        if self.directory is not None:
            self.save('committed')


def recover(data, restore=None):
    recovered = []
    for path in sorted((data / 'backups/install').glob('*/transaction.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        if record.get('schema_version') != 1:
            raise ValueError(f'Unsupported installation journal schema: {path}')
        if record['status'] != 'pending':
            continue
        transaction = Transaction(data)
        transaction.directory = path.parent
        transaction.metadata = record.get('metadata', {})
        def decode(value):
            value = dict(value)
            if value['kind'] == 'file':
                digest = value.pop('blob')
                if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                    raise ValueError('Invalid installation backup digest')
                raw = (path.parent / digest).read_bytes()
                if hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError(f'Corrupt installation backup: {path}')
                value['content'] = raw
            return value
        transaction.entries = [{'path': Path(entry['path']),
                                'before': decode(entry['before']),
                                'after': decode(entry['after'])} for entry in record['entries']]
        transaction.rollback(restore=restore)
        recovered.append(str(path.parent))
    return recovered
