# 06: Goal of the day

**Status:** done (`feature/daily-loop-followups`, 2026-11-15)

The most productive recorded day (2026-10-28) had an explicit constraint ("tomorrow the camera ships back"). Days without one fragmented.

- [x] `/whats-on-today` proposes one goal for the day in one sentence ("today X matters because Y"), derived from the handoff and the checks; the user confirms or rewrites it.
- [x] The confirmed goal is logged (e.g. `log_event.sh goal "<text>"`).
- [x] `/call-it-a-day` reports whether the goal was reached, partly reached or dropped, with one line why, and writes it in the handoff.

## Comments
- 2026-11-15 (Claude): goal proposed in /whats-on-today step 5 and logged as a `goal` row once confirmed; /call-it-a-day judges it (reached / partly / dropped, one line why), writes it under `Generated:` in the handoff and in the sign-off; /how-did-it-go counts the outcomes. `tests/test_daily_events.py` guards the logged text (it passed at once: the logger already accepted free events). The skill instructions are not yet exercised in a real session.
