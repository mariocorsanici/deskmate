# 04: Put Claude behind the Provider adapter

**What to build:** Preserve the Claude Code experience while routing Claude-specific behavior through the shared Provider contract, proving that the new architecture can run an existing Daily loop end to end.

**Blocked by:** 01: Introduce the provider-neutral command; 03: Migrate to shared Project cards.

**Status:** ready-for-agent

**Implementation:** complete (native discovery, slash resolution and installed-hook delivery verified; authenticated full Daily loop remains ticket 14)

- [x] The Claude adapter can discover Work sessions for a requested period.
- [x] It can read usage information and bounded conversation data from synthetic Claude sessions.
- [x] It can launch a new Work session and resume a Claude-owned Work session.
- [x] Hook configuration merges Deskmate entries idempotently and preserves unrelated user configuration.
- [x] Claude continues to discover and invoke the portable skills with its native slash syntax.
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


- 2026-11-03 review follow-up: Native `Claude Code 2.1.317` in normal print
  mode discovered all five portable skills in both its `skills` and
  `slash_commands` catalogs. Stream-json replay resolved `/study-later` and
  `/checkpoint` into native command markup; an unknown slash name remained a raw
  string. After actual `deskmate integration --provider claude`, native
  `/checkpoint` delivered the installed `UserPromptSubmit` hook, creating a
  Claude checkpoint row with the same session ID
  `24060dd6-dced-4ef3-8739-d376198862eb` and project cwd as native output.
  Evidence: `/private/tmp/deskmate-spec-run/native-claude-evidence.md`, with raw
  environment, native output/debug, integration result and log under
  `/private/tmp/deskmate-spec-run/native-claude-standard-5t0ead3m`.
  HOME, CLAUDE_CONFIG_DIR, project and Deskmate data were disposable; the API key
  was a synthetic dummy, the API URL was loopback, and calls ended in deliberate
  connection failure with zero API time/tokens/cost. No real user configuration,
  credentials or conversations were used. The earlier `--bare` evidence was
  insufficient because reduced mode skips filesystem skill discovery; the normal
  mode evidence supersedes that limitation. This closes native discovery,
  invocation parsing/resolution and hook delivery only; authenticated execution
  of skill instructions and the full Daily loop remain manual ticket 14 work.
- 2026-11-03 review fix: Moved native hook configuration lookup, recognition and
  verification payload construction into each Provider adapter under ADR 0001.
  The common facade retains isolated execution and matching activity-row checks.
  A public integration regression reproduced failure on an unrelated malformed
  shell command before the fix and now verifies successful logging while
  preserving that unrelated hook. Both Provider adapter suites passed (33 tests).

- Final review-fix validation (2026-11-03): `python3 -Werror::ResourceWarning -m unittest discover -s tests -q` passed **104 tests, no skips** in 32.185s; `git diff --check` passed. All new regressions were observed RED before their fixes. No user data or protected Git operations were touched.

- Final recheck after resume eligibility fix (2026-11-03), directly in `/private/tmp/deskmate-review-0406`: `python3 -Werror::ResourceWarning -m unittest discover -s tests -q` passed **105 tests, no skips** in 30.726s; `git diff --check` passed. Public coverage retains degraded analytics warnings while allowing valid indexed native resume and rejecting unknown/invalid metadata. Protected Git operations remain parent-owned.
