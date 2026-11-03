# 05: Add the Codex Provider adapter

**What to build:** Make Codex CLI an equal local Provider that can participate in the same Daily loop and shared Project cards using Codex-native skill discovery and session behavior.

**Blocked by:** 01: Introduce the provider-neutral command; 02: Detect and configure Providers; 03: Migrate to shared Project cards.

**Status:** ready-for-agent

**Implementation:** complete; awaiting parent integration review.

- [x] The Codex adapter can discover Work sessions for a requested period.
- [x] It can read usage information and bounded conversation data from synthetic Codex sessions.
- [x] It can launch a new Work session and resume a Codex-owned Work session.
- [x] Hook configuration merges Deskmate entries idempotently and preserves unrelated user configuration.
- [x] Setup explains any Codex trust or hook approval required and can verify that logging works.
- [x] Codex discovers the same portable skills and invokes them with its native dollar syntax.
- [x] A Codex-only Daily loop works through the provider-neutral command.
- [x] Adapter failures return structured errors without corrupting shared state.

## Comments

2026-11-03: Implementation verified in a disposable combined checkout of tickets 04/05/06. `python3 -Werror::ResourceWarning -m unittest discover -s tests -q` passed all 98 tests. Public `bin/deskmate` coverage uses an isolated HOME, CODEX_HOME and data directory, synthetic JSONL/SQLite sessions, and fake Codex/iTerm executables. Permanent tests use only the checked-in public command; no sibling-worktree fallback remains. Parent owns protected Git staging/commit/merge operations and will run final integration review.

The Codex-only command loop covers configuration with Claude unavailable, hook installation plus isolated synthetic verification, new-session and native resume plans, a Codex-owned Checkpoint, live Checks, bounded retrospective reads, native dollar-skill logging, repeated Stop events, separate raw Codex usage, and cached counters after history disappears. Custom CODEX_HOME verification is covered. Unrelated hooks/handlers/empty groups and personal skill collisions are preserved, malformed history degrades, and launch failures return structured results. SQLite connections are explicitly closed.

Runtime evidence: installed `codex-cli 0.166.0` reports native hooks enabled in `codex features list`; `codex --help` and `codex resume --help` establish native launch/resume and persisted hook trust. Read-only schema inspection establishes `state_5.sqlite.threads` and `thread_history_1.sqlite.thread_items`. Running native `codex migrate-rollouts --apply --json` only against wholly synthetic temporary state produced `userMessage`/`agentMessage` SQLite items, which the public command read successfully. No real Work session was launched and no user configuration or conversation data was changed/read.

Official references: [hooks and trust](https://developers.openai.com/codex/hooks), [skill discovery, invocation policy and symlinks](https://developers.openai.com/codex/skills), [app-server message items](https://developers.openai.com/codex/app-server). Installation links the existing shared skill source under `~/.agents/skills`. Each shared skill now has `agents/openai.yaml` with `policy.allow_implicit_invocation: false`, preserving explicit invocation alongside existing Claude frontmatter. Installed Codex native `skills/list` discovered all five linked skills in a temporary home with no parser errors. Broader skill text portability remains ticket 12. Native transcript schemas are unstable; unavailable/unsupported history produces a degraded result and continuation guidance from the Project card and Checks.

Synthetic hook verification proves local logging only. After setup the user must inspect and trust new/changed hooks in Codex `/hooks`, then run a real native skill and inspect its Provider-tagged log row. This manual native delivery/Daily loop check belongs to ticket 14 and is intentionally not claimed by adapter tests.

