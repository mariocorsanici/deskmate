# 11: Make the retrospective progressive

**What to build:** Keep retrospective context small by analysing durable data first, letting the user select relevant Work sessions, and reading bounded Session deltas only where they add value.

**Blocked by:** 03: Migrate to shared Project cards; 06: Make logs and metrics Provider-aware; 08: Extract bounded Session deltas.

**Status:** ready-for-agent

**Implementation:** complete

- [x] The initial retrospective uses metrics, Handoffs, Project cards and logs without reading conversation messages.
- [x] All available candidate Work sessions are listed with Provider identity.
- [x] Deskmate recommends at most five candidates and explains each recommendation.
- [x] The user can add, remove or replace candidates before any Session delta is read.
- [x] Selected sessions are read with the configured bounded limits.
- [x] The user can deepen one unclear session at a time with an explicit one-off limit.
- [x] Transcript adapter failure degrades the affected analysis without stopping the retrospective.
- [x] Provider-specific raw metrics remain visibly distinct in the result.



## Comments

Implemented on 2026-11-10 by session `/root`, scoped to C11. The public
`deskmate retrospective` command collects durable evidence and metadata for both
Providers, lists every candidate, recommends at most five with reasons, and reads
only explicitly chosen bounded deltas. One-off deepening affects one session
and leaves configuration unchanged. Raw native counters retain their Provider,
source and snapshot time; unavailable sources degrade without hiding healthy work.

Baseline 224/224; final full suite **239/239** on Python 3.14.6 with
ResourceWarnings as errors. All **15 retrospective scenarios** also pass on
system Python 3.9.6. Instruction application observed old preselection reads
then verified the new selection pause, replacement, Provider identity and
nonpersistent deepening. An experiment-branch scope bypass and malformed cached
metadata were independently reviewed and fixed with RED/GREEN regressions;
noncanonical dates now fail explicitly instead of silently losing activity.

See `docs/testing/progressive-retrospective.md`. Native authenticated acceptance
remains pending under C14. No personal installation, push or merge in this ticket.
