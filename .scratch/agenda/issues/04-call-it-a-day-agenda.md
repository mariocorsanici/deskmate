# 04: /call-it-a-day writes and tidies the agenda

**Status:** implemented
**Blocked by:** 01

- [x] One-line question for non-development items to add or close; answers written through `tools/agenda.py`.
- [x] `agenda.py archive` for past days.
- [x] If tomorrow is a non-development day, one line in the handoff.

## Comments

2026-11-06: Added one non-development question before handoff writing, CLI-only changes, day archiving, and tomorrow's whole/half-day note with consistent sign-off.

Independent GREEN application checks against temporary CLI fixtures passed: empty answer adds nothing; undated task survives handoff replacement; completion exact line/date; ambiguous completion prints candidates and preserves bytes; default archive moves past days while leaving completed tasks for the retrospective; tomorrow whole-day note says no sessions; half-day note reserves the occupied half; malformed lines are reported, exit 3 wins, and successful exit-2 writes are not repeated. Full suite: 39 tests passing on Python 3.9.6 and 3.14.6. No live installed-skill invocation was performed.
