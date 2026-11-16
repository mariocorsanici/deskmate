#!/usr/bin/env python3
"""Is a retrospective due? One every two development days, used by /whats-on-today.

A development day is a date with at least one `checkpoint` or `call-it-a-day` run in
data/log.csv, from the date of the latest completed retrospective (it runs in the morning,
so that day's work is still to review) up to yesterday. A retrospective is completed when
it logged `how-did-it-go-end`; logs from before end markers fall back to `how-did-it-go`. A date
the agenda reserves as a whole non-development day (travel, leave) does not count, even
if some work was logged on it; half days count. Agenda archives are consulted too.

Usage: retro_due.py [--today YYYY-MM-DD]

Prints one JSON object:
  log_found             false when data/log.csv does not exist yet
  last_retrospective    date of the latest how-did-it-go run, or null
  development_days      the counted dates
  non_development_days  whole non-development days in the period: {date, entry}
  agenda_warnings       invalid agenda lines met while reading, to report
  skipped_rows          log rows whose date could not be read (not counted)
  due                   true at two or more development days
Exit 1, with a message and no traceback, when the log cannot be read.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import agenda  # noqa: E402
import activity_log  # noqa: E402
from activity_log import data_root  # noqa: E402

WORK = {'checkpoint', 'call-it-a-day'}
NEEDED = 2


def non_development_days(start, today):
    """Whole-day agenda entries from start (or the beginning) to yesterday."""
    words = agenda.language()
    paths = [agenda.DATA / 'agenda.md', *sorted((agenda.DATA / 'archive').glob('agenda-*.md'))]
    found, warnings = {}, []
    for path in paths:
        if not path.exists():
            continue
        doc = agenda.Document(path, words, repair=False)
        warnings.extend(doc.invalid)
        for e in doc.entries:
            if e.kind == 'days' and e.part == 'day' and e.date < today and (start is None or e.date >= start):
                found.setdefault(e.date, e.raw)
    return found, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--today', type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args(argv)
    agenda.DATA = data_root()  # one data folder for the log and the agenda, override included
    log = data_root() / 'log.csv'
    if not log.exists():
        print(json.dumps({'log_found': False, 'last_retrospective': None, 'development_days': [],
                          'non_development_days': [], 'agenda_warnings': [], 'skipped_rows': 0, 'due': False}))
        return 0
    try:
        _, rows, _ = activity_log.read_log(log)
    except (ValueError, OSError, UnicodeError) as error:
        print(f'retro_due: cannot read {log}: {error}', file=sys.stderr)
        return 1
    dated, bad = [], 0
    for r in rows:
        try:
            dated.append((dt.date.fromisoformat(r['date']), r['event']))
        except ValueError:
            bad += 1
    ends = [d for d, event in dated if event == 'how-did-it-go-end' and d <= args.today]
    starts = [d for d, event in dated if event == 'how-did-it-go' and d <= args.today]
    retros = ends or starts
    last = max(retros) if retros else None
    try:
        skipped, warnings = non_development_days(last, args.today)
    except (OSError, UnicodeError) as error:
        skipped, warnings = {}, [f'agenda unreadable, non-development days not excluded: {error}']
    days = sorted({d for d, event in dated
                   if event in WORK and (last is None or d >= last) and d < args.today and d not in skipped})
    print(json.dumps({
        'log_found': True,
        'last_retrospective': last.isoformat() if last else None,
        'development_days': [d.isoformat() for d in days],
        'non_development_days': [{'date': d.isoformat(), 'entry': raw} for d, raw in sorted(skipped.items())],
        'agenda_warnings': warnings,
        'skipped_rows': bad,
        'due': len(days) >= NEEDED,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
