# 06: Non-development days in the stale-handoff and development-day rules

**Status:** done (`feature/daily-loop-followups`, 2026-11-15)

- [x] The development-day count for the retrospective (daily-loop-tuning 05) excludes dates where `agenda.py is-dev-day` exits 3.
- [x] The stale-handoff rule (daily-loop-tuning 03) names the non-development days in its opening line ("ieri trasferta Monfalcone"), and still declares the handoff stale across them.
- [x] Tests or a documented manual check for both.

## Comments

2026-11-06: Ticket 01 is implemented and exposes the stable `is-dev-day` interface, including archived dates. This ticket remains blocked until daily-loop-tuning tickets 03/05 land on develop. The current agenda branch deliberately does not rewrite the retrospective cadence or the daily-loop stale-handoff opening. No other feature branch was modified.

2026-11-15 (Claude): `retro_due.py` skips dates where the agenda (or its archive) holds a whole-day entry and lists them as `non_development_days`; half days count. `is-dev-day` now prints the whole-day entry on exit 3, which `/whats-on-today` step 1 uses to name the non-development days in the stale-handoff line while still declaring the handoff stale. Tests: `tests/test_retro_due.py` (A06 cases), `tests/test_agenda.py::test_is_dev_day_prints_the_whole_day_entry`.
