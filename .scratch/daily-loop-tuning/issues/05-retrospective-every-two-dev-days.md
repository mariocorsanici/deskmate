# 05: Retrospective every two development days

**Status:** needs-triage (experiment, confirm at the next /how-did-it-go)

Fixed weekdays (Mon/Wed/Fri) did not hold on busy weeks and ignore travel days. The user proposed: one retrospective every two development days (works Mon–Fri).

- [ ] A development day is a day with at least one `checkpoint` or `call-it-a-day` row in `log.csv`.
- [ ] `/whats-on-today` counts development days since the last `how-did-it-go`; at two or more, it proposes the retrospective as the **first** step of the day (about 10 minutes), not as a missed-step note.
- [ ] `/call-it-a-day` and `/whats-on-today` stop using the Mon/Wed/Fri rule.
- [ ] `/how-did-it-go` keeps each section to at most three points.

## Comments
- 2026-11-06 (Claude, for Mario): `feature/agenda` adds `tools/agenda.py is-dev-day`. This ticket stays log-based; ticket 06 of `.scratch/agenda/` will make it skip non-development days once both branches are on `develop`.
