# Pre-merge Provider Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve C15, C16, cold Codex history and normal native session closing before integration.

**Architecture:** Keep native differences in adapters. Share private iTerm launch transport and process verification; isolate cold SQLite recovery behind a read-only storage boundary. Diagnose closing using actual native lifecycle evidence, without fabricating events.

**Tech Stack:** Python 3.9+ standard library, zsh, iTerm AppleScript, native Claude/Codex, SQLite.

**Spec:** `docs/superpowers/specs/2026-11-15-premerge-reliability-design.md`

## Global Constraints

- Do not mutate native provider databases or ignore live WAL.
- Native hooks alone establish native identity and ownership; process checks establish process liveness only.
- Private prompt files use mode 0600, private directories 0700, and disappear after consumption/failure.
- Startup wait is bounded to about ten seconds, scoped to the returned iTerm tty; resume receives the same check.
- Morning is displayed once per local working date, within the existing -5-minute/+3-hour window, claimed before waiting for a response; evening behavior is preserved.
- Isolated test data only; no calendar work, personal integration install, push or merge.

## Review Focus

- Native writer appearing during cold-copy fallback: reject/retry without stale complete-coverage claims.
- Long quoted/multiline prompts and wrong-provider processes on the right tty: literal delivery and truthful startup failure.
- Concurrent login/scheduled triggers and a still-open morning alert: one display, no early response-dependent claim.
- Early native hooks and fast process exit: preserve ownership revision rules and truthful launch/journal states.
- Normal new/resume native exit: actual SessionEnd and ended evidence, no masked UI automation error.

## Task 1: Morning reminder recovery (independent)

Files: `tools/reminders.py`, `tools/morning_reminder.sh`, `tools/installation.py`, `tests/test_reminders.py`, `tests/test_installation.py`, C16 ticket, dedicated verification note.

Consumes config/provider rendering and transactional LaunchAgent activation. Produces login-triggered once-per-working-date morning display with unchanged evening behavior.

- [x] Write and observe failing working-day/time-window, concurrent duplicate, display-before-answer and LaunchAgent upgrade tests.
- [x] Implement bounded display claiming and RunAtLoad, retaining transactional activation/rollback.
- [x] Run reminder/installation tests, record RED/GREEN and relevant full-suite result.

## Task 2: Persisted cold Codex history (independent)

Files: new focused native SQLite helper if needed; only storage sections of `tools/adapter_codex.py`; storage/adapter tests and dedicated verification note.

Consumes provider-owned metadata/history SQLite databases. Produces complete cold metadata/messages and unchanged live WAL freshness, without native mutation.

- [x] Reproduce the recorded cold read on disposable actual-schema files; add a public failing post-exit message/coverage regression.
- [x] Implement stable private cold snapshots; reject sidecars, changed/replaced files and unsupported/corrupt copies; clean private storage on all paths. Actual native acceptance exposed sidecar creation by successful mode=ro, so known cold sources now use snapshots proactively.
- [x] Verify cold native bytes/sidecar set unchanged, fresh committed live WAL included, race refusal, malformed schemas and cleanup on Python 3.14 and 3.9.

## Task 3: Verified native startup (root)

Files: focused shared terminal transport helper, launch sections of both adapters, `tools/work_sessions.py` only for returned startup diagnostics, affected launch fixtures/tests, C15 ticket.

Consumes native argv and selected environment. Produces a short private-payload iTerm command, returned tty/session metadata, real matching native process evidence or bounded actionable failure. Native hook ownership remains separate.

- [x] Observe public regressions for >1000-character literal prompts, multiline/quotes, missing process and wrong-provider process on tty, resume and failure cleanup.
- [x] Implement private payload consumption, iTerm tty return and bounded process verification; retain inspectable failed tab.
- [x] Run both-adapter routing/launch/transfer tests and full suite; document changed fake-terminal fixtures as boundary updates, not proof of native operation.

## Task 4: Native closing and integrated acceptance (root)

Consumes completed Tasks 1–3 and a diagnosis of the old closing harness. Produces real new/resume startup/normal exit evidence and a ready-to-review branch with all four owner requirements accounted for.

- [x] Diagnose the old UI input problem in isolation; use an unambiguous normal exit mechanism in fresh fixtures.
- [x] If a production defect reproduces, first add its failing lifecycle regression, then fix without inventing native events. No additional native closing defect reproduced; harness assumptions were corrected, not native journals.
- [x] Exercise actual new/resume start and normal exit for both providers; assert matching SessionEnd/ended journal and no leftover fixture process.
- [x] Exercise Codex post-exit cold reads with known native conversation content and absent history sidecars; prove no native data/file-set mutation. Metadata retained its legitimate WAL/SHM pair.
- [x] Verify reminder login/once-per-day behavior with isolated deterministic time and an actual RunAtLoad/native alert, concurrent calls and same-day reload; no reboot or personal LaunchAgent changes.
- [x] Run full suite and system-Python relevant suites, obtain final independent review, update all tickets/current integration gate, apply reviewed bytes to the original feature worktree and commit focused results. Do not merge.

## Recorded result

All four requirements passed automated and actual native acceptance. Candidate
308/308; system Python 131/131; original feature destination 308/308. Exact
intermediate index exports additionally passed all 53 C16 and 35 Codex storage
tests before their focused local commits. Final C15 commit preserves the shared
transport and integrated evidence. Native production bytes match the destination;
test processes, temporary authentication references and unique LaunchAgents were
removed. Details and bounded native limitations:
[durable verification](../../testing/premerge-reliability-2026-11-15.md).
No push, merge, calendar work or personal integration installation.
