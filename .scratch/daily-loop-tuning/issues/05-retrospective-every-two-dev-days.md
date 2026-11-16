# 05: Retrospective every two development days

**Status:** done (`feature/daily-loop-followups`, 2026-11-15)

Fixed weekdays (Mon/Wed/Fri) did not hold on busy weeks and ignore travel days. The user proposed: one retrospective every two development days (works Mon–Fri).

- [x] A development day is a day with at least one `checkpoint` or `call-it-a-day` row in `log.csv`.
- [x] `/whats-on-today` counts development days since the last `how-did-it-go`; at two or more, it proposes the retrospective as the **first** step of the day (about 10 minutes), not as a missed-step note.
- [x] `/call-it-a-day` and `/whats-on-today` stop using the Mon/Wed/Fri rule.
- [x] `/how-did-it-go` keeps each section to at most three points.

## Comments
- 2026-11-06 (Claude, for Mario): `feature/agenda` adds `tools/agenda.py is-dev-day`. This ticket stays log-based; ticket 06 of `.scratch/agenda/` will make it skip non-development days once both branches are on `develop`.
- 2026-11-15 (Claude): implemented with `tools/retro_due.py` (log-based count, JSON output, tests in `tests/test_retro_due.py`). The evening reminder line now reads "(if /whats-on-today proposed it)" instead of the weekdays. Agenda ticket 06 landed in the same change: whole non-development days are excluded from the count.
