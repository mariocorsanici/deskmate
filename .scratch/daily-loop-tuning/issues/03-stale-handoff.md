# 03: Declare a stale handoff

**Status:** ready-for-agent

Today's step 1 only checks whether the handoff is from the previous working day. A day off in between (travel, leave) leaves the handoff formally "previous day" but the world moved.

- [ ] `/whats-on-today` computes the gap between the handoff's timestamp and now, and the days in between with no deskmate activity in `log.csv`.
- [ ] If there is at least one such day, the reply opens with one line: the handoff is from <date>, <n> days without work in between, state taken from the live checks, not from the handoff.
- [ ] In that case "Where you are" items are reported from the checks and ticket 02's list; the handoff is used only for intent ("To do", "Before you start").

## Comments
- 2026-11-06 (Claude, for Mario): `feature/agenda` adds `tools/agenda.py is-dev-day`. This ticket stays log-based; ticket 06 of `.scratch/agenda/` will make it skip non-development days once both branches are on `develop`.
