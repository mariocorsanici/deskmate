# 03: Declare a stale handoff

**Status:** ready-for-agent

**Implementation:** complete (automated/local verification; native acceptance not claimed).

Today's step 1 only checks whether the handoff is from the previous working day. A day off in between (travel, leave) leaves the handoff formally "previous day" but the world moved.

- [x] `/whats-on-today` computes the gap between the handoff's timestamp and now, and the days in between with no deskmate activity in `log.csv`.
- [x] If there is at least one such day, the reply opens with one line: the handoff is from <date>, <n> days without work in between, state taken from the live checks, not from the handoff.
- [x] In that case "Where you are" items are reported from the checks and ticket 02's list; the handoff is used only for intent ("To do", "Before you start").

## Comments

Implemented 2026-11-06. Handoffs record creation time separately from their target day; morning instructions count inactive intervening dates and use live facts. Calendar/timezone scenarios were replayed; unavailable-evidence behavior was instruction-reviewed. See `docs/testing/daily-loop-tuning.md`.
