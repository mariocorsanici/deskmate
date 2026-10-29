# 09: Implement a degradable Provider switch

**What to build:** Let the user explicitly continue a project with the other Provider from durable state, including when the source Provider is exhausted and its transcript cannot be read.

**Blocked by:** 03: Migrate to shared Project cards; 07: Route Work session launch and resume.

**Status:** ready-for-agent

- [ ] The user can explicitly select Claude or Codex as the target Provider.
- [ ] A Provider switch always creates a new target Work session rather than claiming to resume the source session.
- [ ] The target receives the current Project card and results of current Checks.
- [ ] An unavailable source Provider does not prevent the switch.
- [ ] An unavailable or unreadable transcript produces a clear warning and a card-plus-Checks transfer.
- [ ] The target is instructed to ask the user only for missing context.
- [ ] A potentially simultaneous Work session on the same project triggers an explicit warning and confirmation.
- [ ] Cancelling the confirmation leaves Project card ownership unchanged.

