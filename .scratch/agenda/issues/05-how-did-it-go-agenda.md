# 05: /how-did-it-go reports closed agenda tasks

**Status:** done (merged into develop as `1420b75`, 2026-11-15)
**Blocked by:** 01

- [x] One line with the tasks closed since the last retrospective (`list --closed-since`).
- [x] Then `archive --closed-before <today>`.

## Comments

2026-11-06: Retrospective collects `list --closed-since` evidence before reporting/recording, then archives tasks closed strictly before today.

Independent GREEN application checks with today 2026-11-06/start 2026-11-04 passed: empty completion list; both yesterday and today retained in the report; yesterday moves by completion month while today's completion remains active; older completion excluded from report; invalid lines preserved/reported on exit 2 without duplicate retry; exit 1 is resolved instead of treated as an empty agenda. Full suite: 39 tests passing; shell syntax checks passed. These are temporary CLI and instruction application checks, not live installed-skill runs.

Final review: one separator-validation issue fixed after observing its regression fail in all ten affected add/day cases. Complete suites pass 40/40 on Python 3.9.6 and 3.14.6; both shell files pass individual syntax checks. See `../verification.md` for the review evidence and scope decisions.
