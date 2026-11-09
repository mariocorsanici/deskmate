# 09: Implement a degradable Provider switch

**What to build:** Let the user explicitly continue a project with the other Provider from durable state, including when the source Provider is exhausted and its transcript cannot be read.

**Blocked by:** 03: Migrate to shared Project cards; 07: Route Work session launch and resume.

**Status:** ready-for-agent

**Implementation:** complete (synthetic command/PTY acceptance; protected deltas follow ticket 10).

- [x] The user can explicitly select Claude or Codex as the target Provider.
- [x] A Provider switch always creates a new target Work session rather than claiming to resume the source session.
- [x] The target receives the current Project card and results of current Checks.
- [x] An unavailable source Provider does not prevent the switch.
- [x] An unavailable or unreadable transcript produces a clear warning and a card-plus-Checks transfer.
- [x] The target is instructed to ask the user only for missing context.
- [x] A potentially simultaneous Work session on the same project triggers an explicit warning and confirmation.
- [x] Cancelling the confirmation leaves Project card ownership unchanged.


## Comments

2026-11-09: Implemented explicit new-Provider continuation via `deskmate switch`, current Checks, conservative overlap warning and real TTY confirmation. Cancellation and failed launch preserve source ownership; only correlated native hook evidence claims the new identity. Context is passed via a private file path. Initial context is card-plus-Checks; no raw transcript is sent before ticket 10 protection. Six public command/PTY regressions passed after RED; full suite 163/163 passes with ResourceWarnings as errors. Both source-unavailable directions are covered. Native model acceptance remains pending.
