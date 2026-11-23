# 03: /whats-on-today reads the agenda

**Status:** done (merged into develop as `1420b75`, 2026-11-15)
**Blocked by:** 01

- [x] Whole non-development day: said first, only the agenda block, no project checks or sessions unless asked.
- [x] Half day: the development plan covers only the other half.
- [x] "Non sviluppo" block before the suggested order, from `agenda.py list` (due, deadline highlighted, undated count, upcoming days).
- [x] Missed-steps check skips dates where `agenda.py is-dev-day` exits 3.
- [x] Invalid agenda lines (exit 2) are reported in one line.

## Comments

2026-11-06: Added an agenda guard before handoff reads/checks/session opening; half-day availability and the Non sviluppo block are independent additions. Missed-step dates consult `is-dev-day`, including monthly archives, while handoff age still uses the actual previous weekday.

Independent GREEN application checks against temporary CLI fixtures passed for: whole day plus stale handoff/broken checks (agenda only); morning-only reservation (afternoon plan); both half days (no free slot, is-dev-day stays 0); malformed lines with exit 3 winning over 2 (all diagnostics shown); no reservation (normal workflow); archived Thursday travel skipped for missed steps while Wednesday handoff remains stale on Friday. Existing read bytes were unchanged. Full automated suite: 39 passing tests. These are instruction application checks, not live installed-skill runs.
