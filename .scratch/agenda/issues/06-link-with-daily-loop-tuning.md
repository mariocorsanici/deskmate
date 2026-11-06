# 06: Non-development days in the stale-handoff and development-day rules

**Status:** blocked
**Blocked by:** tickets 03 and 05 of `.scratch/daily-loop-tuning/` merged into `develop`

- [ ] The development-day count for the retrospective (daily-loop-tuning 05) excludes dates where `agenda.py is-dev-day` exits 3.
- [ ] The stale-handoff rule (daily-loop-tuning 03) names the non-development days in its opening line ("ieri trasferta Monfalcone"), and still declares the handoff stale across them.
- [ ] Tests or a documented manual check for both.

## Comments

2026-11-06: Ticket 01 is implemented and exposes the stable `is-dev-day` interface, including archived dates. This ticket remains blocked until daily-loop-tuning tickets 03/05 land on develop. The current agenda branch deliberately does not rewrite the retrospective cadence or the daily-loop stale-handoff opening. No other feature branch was modified.
