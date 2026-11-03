# 04: Put Claude behind the Provider adapter

**What to build:** Preserve the Claude Code experience while routing Claude-specific behavior through the shared Provider contract, proving that the new architecture can run an existing Daily loop end to end.

**Blocked by:** 01: Introduce the provider-neutral command; 03: Migrate to shared Project cards.

**Status:** ready-for-agent

**Implementation:** complete (live native skill invocation requires manual validation)

- [x] The Claude adapter can discover Work sessions for a requested period.
- [x] It can read usage information and bounded conversation data from synthetic Claude sessions.
- [x] It can launch a new Work session and resume a Claude-owned Work session.
- [x] Hook configuration merges Deskmate entries idempotently and preserves unrelated user configuration.
- [ ] Claude continues to discover and invoke the portable skills with its native slash syntax.
- [x] A Claude-only Daily loop works through the provider-neutral command.
- [x] Adapter failures return structured errors without corrupting shared state.

## Comments

- 2026-11-03: Implemented the Claude adapter and shared `sessions`, `session`,
  `provider-launch`, and `integration` command facade. Synthetic command-boundary
  tests cover metadata-only indexed discovery, requested periods, safe malformed
  transcript handling, usage-only reads, bounded conversation reads, launch plans,
  iTerm quoting/failure, and idempotent hook/skill installation and removal.
  `integration --verify` executes the installed prompt hook under disposable
  HOME/data and validates a Claude checkpoint event without writing user logs.
  A temporary runtime combining this ticket with ticket 06's current hook helper
  passed **63 tests, no skips** (53 baseline plus 10 adapter scenarios). Final
  acceptance remains open until ticket 06 is integrated and the full suite runs
  directly from the worktree; no real native Work session has been launched.
- 2026-11-03: Final integrated validation after merging ticket 06 (`56ec840`):
  `python3 -m unittest discover -s tests -q` passed **79 tests, no skips**,
  including the original 53 tests. `git diff --check` passed. Merging the latest
  `feature/codex-cli-support` reported already up to date. The synthetic Claude
  Daily loop exercises slash-command hook logging for morning planning,
  Checkpoint, retrospective and Handoff, shared card ownership and Checks,
  metadata-only discovery, conversation reads and same-Provider resume plans.
  Additional verified fixes reject option-shaped native IDs, preserve unrelated
  empty hook configuration, and degrade malformed index fields. Shared hook
  verification respects custom `CODEX_HOME`; a disposable runtime using ticket
  05's adapter demonstrated RED then GREEN for that case. Shared skill symlinks
  and native slash-command logging are verified, but live Claude discovery and
  invocation remain unchecked because no real Work session was launched.

