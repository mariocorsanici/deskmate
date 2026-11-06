# Agenda verification — 2026-11-06

Tickets 01–05 are implemented. Ticket 06 remains blocked on daily-loop-tuning
tickets 03/05 reaching develop. Keep this work on feature/agenda for the
integration order in coordination.md.

## Automated evidence

- `python3 -I -B -m unittest discover -s tests -v`: 40 tests pass on Python 3.14.6.
- `/usr/bin/python3 -I -B -m unittest discover -s tests -v`: 40 tests pass on Python 3.9.6.
- `zsh -n install.sh` and `zsh -n tools/hook_log.sh`: both pass.
- `git diff --check`: passes.

The tests execute actual CLI/hook subprocesses in temporary roots. They cover
both languages, preservation of unrelated bytes, invalid input, JSON buckets,
matching, day replacement, locking/concurrent first use, archiving and historical
development-day lookup. No installed personal data was used.

## Agent application checks

An independent agent first evaluated the original instructions, then applied
each new/modified skill against temporary CLI fixtures. Agenda phrases,
same-weekday ambiguity, duplicate matches, whole/half-day mornings, archived
travel days, evening updates, tomorrow notes and retrospective cleanup passed.
Ticket comments hold the exact scenarios. These checks are narrower than a live
installed-skill invocation.

The real install.sh Data block also passed temporary-root checks for Italian
initialization, repeat installation and byte-identical preservation of an
existing damaged agenda. No global installer actions were run.

## Independent final review

Reviewed range: 70468e3..8b08675. No Critical or Minor findings. One Important
finding: vertical-tab, form-feed and ASCII file/group/record separators passed
description validation but were split into extra lines on the next read.

Regression `test_all_line_separators_rejected_before_add_or_day` first failed
in all 10 affected add/day subcases. Validation now rejects every line separator
recognized by the parser. The regression passes and both full suites pass 40/40.
No second review was needed for this isolated fix; its real CLI regression
demonstrates rejection without changing the file.

## Review scope decisions

- Ticket 06 and branch reconciliation stay deferred as agreed. Cost: its cadence
  and stale-handoff wording changes require the later integration step.
- Live installed-skill behavior is left for acceptance after integration. Cost:
  subprocess/scenario checks do not establish end-to-end installed behavior.
- Holidays and calendar integration remain outside scope. Cost: working-day
  windows use Monday–Friday and do not exclude public holidays.
- Atomic replacement applies per file, without a transaction across every monthly
  archive. Archives are written before removing active entries. Cost: interruption
  between those writes can leave duplicate archive entries needing cleanup;
  cross-file crash recovery is not part of this change.
