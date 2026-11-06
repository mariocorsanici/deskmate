#!/usr/bin/env python3
"""Own the non-development agenda; run with python3 -I tools/agenda.py --help.

list writes one JSON object to stdout. Other commands print affected entry
lines. Notices and diagnostics are stderr; exit codes are 0 (clean), 1
(usage, no agenda writes), 2 (invalid lines), 3 (whole non-development day).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata


DATA = Path(__file__).resolve().parent.parent / 'data'
SEP = ' · '
LINE_BREAKS = '\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029'
WORDS = {
    'en': {'days': 'Days', 'tasks': 'Tasks', 'day': 'day', 'morning': 'morning',
           'afternoon': 'afternoon', 'when': 'when', 'due': 'due', 'done': 'done',
           'intro': 'Non-development days and tasks. Dates are a reference, not a constraint.',
           'created': 'created', 'section': 'section recreated', 'invalid': 'invalid',
           'replaced': 'replaced', 'before': 'deadline before planned date',
           'weekend': 'weekend date', 'none': 'no matching entry',
           'many': 'multiple matches; choose a more specific description'},
    'it': {'days': 'Giorni', 'tasks': 'Attività', 'day': 'giornata', 'morning': 'mattina',
           'afternoon': 'pomeriggio', 'when': 'quando', 'due': 'entro', 'done': 'fatto',
           'intro': 'Giorni e attività non di sviluppo. Le date sono un riferimento, non un vincolo.',
           'created': 'creato', 'section': 'sezione ricreata', 'invalid': 'non valida',
           'replaced': 'sostituito', 'before': 'scadenza prima della data prevista',
           'weekend': 'data nel weekend', 'none': 'nessuna voce corrispondente',
           'many': 'più corrispondenze; scegliere una descrizione più specifica'},
}
SECTIONS = {'## ' + words[key]: key for words in WORDS.values() for key in ('days', 'tasks')}
PARTS = {words[key]: key for words in WORDS.values() for key in ('day', 'morning', 'afternoon')}
LABELS = {words[key]: key for words in WORDS.values() for key in ('when', 'due', 'done')}


class UsageError(ValueError):
    pass


def date_value(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('expected YYYY-MM-DD: ' + value)
    return dt.date.fromisoformat(value)


def cli_date(value):
    try:
        return date_value(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def description(value):
    if not value.strip() or SEP in value or any(c in value for c in LINE_BREAKS):
        raise argparse.ArgumentTypeError('use a non-empty, single-line description without " · "')
    return value.strip()


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def parser():
    result = Parser(description=__doc__)
    commands = result.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add', help='add a non-development task')
    add.add_argument('description', type=description)
    add.add_argument('--when', type=cli_date)
    add.add_argument('--due', type=cli_date)
    day = commands.add_parser('day', help='reserve a day or half day')
    day.add_argument('date', type=cli_date)
    day.add_argument('part', choices=('day', 'morning', 'afternoon'))
    day.add_argument('description', type=description)
    for name in ('done', 'remove'):
        command = commands.add_parser(name)
        command.add_argument('text', type=description)
        if name == 'done':
            command.add_argument('--today', type=cli_date, help='completion date, default today')
    listing = commands.add_parser('list', help='print JSON with agenda buckets')
    listing.add_argument('--today', type=cli_date)
    listing.add_argument('--closed-since', type=cli_date)
    development = commands.add_parser('is-dev-day', help='exit 3 for a whole non-development day')
    development.add_argument('date', type=cli_date)
    archive = commands.add_parser('archive', help='archive past days and optionally closed tasks')
    archive.add_argument('--today', type=cli_date)
    archive.add_argument('--closed-before', type=cli_date)
    return result


@dataclass
class Entry:
    index: int
    kind: str
    raw: str
    description: str
    date: dt.date | None = None
    part: str | None = None
    when: dt.date | None = None
    due: dt.date | None = None
    closed: dt.date | None = None


def parse_entry(index, kind, raw):
    """A malformed metadata suffix is invalid, never part of a description."""
    try:
        if kind == 'days':
            fields = raw.split(SEP)
            if len(fields) != 3 or not fields[0].startswith('- ') or not fields[2].strip():
                return None
            return Entry(index, kind, raw, fields[2], date=date_value(fields[0][2:]), part=PARTS[fields[1]])
        match = re.fullmatch(r'- \[([ x])\] (.+)', raw)
        if not match:
            return None
        fields = match[2].split(SEP)
        if not fields[0].strip():
            return None
        metadata, last = {}, -1
        for field in fields[1:]:
            item = re.fullmatch(r'(when|quando|due|entro): (\d{4}-\d{2}-\d{2})', field)
            if item is None:
                item = re.fullmatch(r'(done|fatto) (\d{4}-\d{2}-\d{2})', field)
            if item is None:
                return None
            key = LABELS[item[1]]
            order = ('when', 'due', 'done').index(key)
            if order <= last:
                return None
            last = order
            metadata['closed' if key == 'done' else key] = date_value(item[2])
        if (match[1] == 'x') != ('closed' in metadata):
            return None
        return Entry(index, kind, raw, fields[0], **metadata)
    except (KeyError, ValueError):
        return None


class Document:
    """Keep original lines so edits never normalize unrelated user content."""
    def __init__(self, path, words, repair=True):
        self.path, self.words = path, words
        self.original = path.read_bytes() if path.exists() else None
        content = self.original.decode('utf-8', errors='surrogateescape') if self.original is not None else ''
        self.lines = content.splitlines(keepends=True)
        self.newline = '\r\n' if '\r\n' in content else '\n'
        self.notices = []
        if self.original is None:
            self.lines = (f'# Agenda\n\n{words["intro"]}\n\n## {words["days"]}\n\n## {words["tasks"]}\n').splitlines(keepends=True)
            self.notices.append(f'{path.name}: {words["created"]}')
        self.entries, self.invalid = self.scan()
        if repair:
            found = {SECTIONS.get(line.rstrip('\r\n')) for line in self.lines}
            for kind in ('days', 'tasks'):
                if kind not in found:
                    self.insert(len(self.lines), f'## {words[kind]}')
                    self.notices.append(f'{path.name}: {words["section"]}: ## {words[kind]}')

    def scan(self):
        current, entries, invalid = None, [], []
        for index, line in enumerate(self.lines):
            raw = line.rstrip('\r\n')
            if raw in SECTIONS:
                current = SECTIONS[raw]
            elif re.match(r'^#{1,6}\s', raw):
                current = None
            elif current and raw.strip():
                entry = parse_entry(index, current, raw)
                if entry is None:
                    invalid.append(f'{self.path.name}:{index + 1}: {self.words["invalid"]}: {raw}')
                else:
                    entries.append(entry)
        return entries, invalid

    def insert(self, index, raw):
        if index and not self.lines[index - 1].endswith(('\n', '\r')):
            self.lines[index - 1] += self.newline
        self.lines.insert(index, raw + self.newline)

    def append(self, kind, raw):
        start = next(i for i, line in enumerate(self.lines) if SECTIONS.get(line.rstrip('\r\n')) == kind)
        end = start + 1
        while end < len(self.lines) and not re.match(r'^#{1,6}\s', self.lines[end]):
            end += 1
        while end > start + 1 and not self.lines[end - 1].strip():
            end -= 1
        self.insert(end, raw)

    def save(self):
        content = ''.join(self.lines).encode('utf-8', errors='surrogateescape')
        if content == self.original:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix='.agenda-', delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))


def find_one(entries, text, words):
    found = [entry for entry in entries if folded(text) in folded(entry.description)]
    if not found:
        raise UsageError(words['none'])
    if len(found) != 1:
        raise UsageError(words['many'] + '\n' + '\n'.join(entry.raw for entry in found))
    return found[0]


def workday_bound(today, count):
    while count:
        today += dt.timedelta(days=1)
        if today.weekday() < 5:
            count -= 1
    return today


def buckets(entries, today, closed_since):
    days = [e for e in entries if e.kind == 'days']
    tasks = [e for e in entries if e.kind == 'tasks' and e.closed is None]
    return {
        'today': [e.raw for e in days if e.date == today],
        'due': [e.raw for e in tasks if e.when is not None and e.when <= today],
        'deadline': [e.raw for e in tasks if e.due is not None and e.due <= workday_bound(today, 3)],
        'undated': sum(e.when is None and e.due is None for e in tasks),
        'upcoming': [e.raw for e in days if today < e.date <= workday_bound(today, 5)],
        'closed': [e.raw for e in entries if e.closed is not None and closed_since is not None and closed_since <= e.closed <= today],
    }


def date_notices(dates, words):
    return [f'{words["weekend"]}: {value}' for value in dates if value is not None and value.weekday() >= 5]


def operate(args, doc, words):
    """Return stdout, notices, extra documents, and a whole-day flag."""
    entries, output, notices, extra = doc.entries, [], [], []
    today = getattr(args, 'today', None) or dt.date.today()
    if args.command == 'list':
        output.append(json.dumps(buckets(entries, today, args.closed_since), ensure_ascii=True))
    elif args.command == 'add':
        raw = '- [ ] ' + args.description
        for key in ('when', 'due'):
            value = getattr(args, key)
            if value is not None:
                raw += f'{SEP}{words[key]}: {value}'
        doc.append('tasks', raw)
        output.append(raw)
        if args.when is not None and args.due is not None and args.due < args.when:
            notices.append(words['before'])
        notices.extend(date_notices([args.when, args.due], words))
    elif args.command == 'day':
        raw = f'- {args.date}{SEP}{words[args.part]}{SEP}{args.description}'
        overlap = [e for e in entries if e.kind == 'days' and e.date == args.date
                   and ('day' in (e.part, args.part) or e.part == args.part)]
        if overlap:
            first = overlap[0]
            ending = doc.lines[first.index][len(first.raw):]
            doc.lines[first.index] = raw + ending
            for entry in reversed(overlap[1:]):
                del doc.lines[entry.index]
            notices.extend(f'{words["replaced"]}: {e.raw}' for e in overlap)
        else:
            doc.append('days', raw)
        output.append(raw)
        notices.extend(date_notices([args.date], words))
    elif args.command in ('done', 'remove'):
        eligible = [e for e in entries if e.kind == 'tasks' and e.closed is None] if args.command == 'done' else entries
        entry = find_one(eligible, args.text, words)
        if args.command == 'remove':
            del doc.lines[entry.index]
            output.append(entry.raw)
        else:
            raw = entry.raw.replace('- [ ] ', '- [x] ', 1) + f'{SEP}{words["done"]} {today}'
            ending = doc.lines[entry.index][len(entry.raw):]
            doc.lines[entry.index] = raw + ending
            output.append(raw)
    elif args.command == 'archive':
        selected = [e for e in entries if (e.kind == 'days' and e.date < today)
                    or (e.closed is not None and args.closed_before is not None and e.closed < args.closed_before)]
        archives = {}
        for entry in selected:
            month = (entry.date if entry.kind == 'days' else entry.closed).strftime('%Y-%m')
            if month not in archives:
                archives[month] = Document(DATA / 'archive' / f'agenda-{month}.md', words)
            archives[month].append(entry.kind, entry.raw)
            output.append(f'{archives[month].path.name}: {entry.raw}')
        for entry in sorted(selected, key=lambda e: e.index, reverse=True):
            del doc.lines[entry.index]
        extra.extend(archives.values())
    elif args.command == 'is-dev-day':
        archive_path = DATA / 'archive' / f'agenda-{args.date:%Y-%m}.md'
        if archive_path.exists():
            archive = Document(archive_path, words, repair=False)
            extra.append(archive)
            entries = entries + archive.entries
        whole_day = any(e.kind == 'days' and e.date == args.date and e.part == 'day' for e in entries)
        return output, notices, extra, whole_day
    return output, notices, extra, False


def language():
    try:
        config = json.loads((DATA / 'config.json').read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return WORDS['en']
    return WORDS.get(config.get('language'), WORDS['en'])


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        words = language()
        DATA.mkdir(parents=True, exist_ok=True)
        with (DATA / '.agenda.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            doc = Document(DATA / 'agenda.md', words)
            try:
                output, notices, extra, whole_day = operate(args, doc, words)
            except UsageError:
                for line in doc.invalid:
                    print(line, file=sys.stderr)
                raise
            documents = [*extra, doc]
            for item in documents:
                if args.command != 'is-dev-day' or item is doc:
                    item.save()
            for item in documents:
                for line in item.notices + item.invalid:
                    print(line, file=sys.stderr)
            for line in notices:
                print(line, file=sys.stderr)
            for line in output:
                print(line)
            return 3 if whole_day else 2 if any(item.invalid for item in documents) else 0
    except (UsageError, OSError, UnicodeError, OverflowError) as error:
        print(f'agenda: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
