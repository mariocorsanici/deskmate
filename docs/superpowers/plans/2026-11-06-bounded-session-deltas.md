# Bounded Session deltas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement provider-neutral CLI ticket 08 without opening a Provider or transferring context.

**Architecture:** Extend the existing adapter readers with an optional streaming message consumer. A shared Session delta module resolves the latest saved Checkpoint, selects early and recent conversation within two budgets, and exposes a stable command. Native metadata, reasoning and tool results never become delta messages.

**Tech Stack:** Python standard library, unittest, existing Claude JSONL and Codex JSONL/SQLite readers.

**Spec:** `.scratch/provider-neutral-cli/issues/08-bounded-session-deltas.md` and `.scratch/provider-neutral-cli/spec.md`.

## Global Constraints

- Continue on the existing `feature/codex-cli-support` worktree; no changes to other branches, no push or merge.
- Default limits: 12 messages and 6,000 characters. Config `session_delta.max_messages` / `max_characters`; one-command `--max-messages` / `--max-characters` overrides. Validate positive integers without writing configuration.
- Public command: `deskmate [--json] session-delta --provider claude|codex --session-id ID [--after ISO_TIMESTAMP] [--max-messages N] [--max-characters N] [--format text|json]`.
- Resolve a Checkpoint from the shared Project card only when its recorded session and Provider match the requested session. `--after` supplies an explicit timezone-aware boundary. A bare native skill invocation does not prove a saved Checkpoint.
- Legacy card timestamps have minute precision and local timezone: disclose the estimated boundary and partial coverage. No matching saved Checkpoint means bounded coverage from session start, stated explicitly.
- Scan native records incrementally, retaining at most the bounded head/tail candidates; never construct the full conversation list in delta mode. Preserve existing session/discovery/usage behavior.
- Degraded transcript results return exit 0 and structured warnings; invalid options/configuration return exit 2. No model requests, installed personal data, redaction or Provider switching in this ticket.

## Review Focus

- Wrong Provider/session ownership must not cut away another session's unsaved work.
- Huge early/latest messages and a one-character budget must respect both limits and keep recent context.
- Invalid timestamps, malformed Unicode/JSON/SQLite items and missing history must disclose partial/unavailable coverage, with no traceback or raw transcript in warnings.
- Metadata, skill instructions, raw tool results and sidechains must be excluded in all three native storage forms.
- Readers must stream in delta mode while their existing full-session and usage contracts remain unchanged.

### Task 1: Bounded extraction through the stable command

**Files:** Create `tools/session_delta.py`, `tests/test_session_delta.py`; modify `tools/adapter_claude.py`, `tools/adapter_codex.py`, `bin/deskmate`, README, ticket 08 and the progress note.

**Interfaces:** `read_session(session_id: str, *, on_message=None) -> dict` in each adapter retains metadata/warnings but sends normalized messages to `on_message(message, session)` instead of building `messages` when supplied. `read_delta(session_id: str, *, max_messages: int = 12, max_characters: int = 6000, after: str | None = None) -> dict` in each adapter delegates the common selection contract. `session_delta.extract(provider, session_id, reader, *, max_messages, max_characters, after) -> dict` owns the result schema.

- [x] Add public-command tests for all native stores, saved Checkpoint filtering, cancelled invocation, ownership mismatch, tool/metadata exclusion, exact default limits, head/tail selection, tiny and Unicode budgets, configuration overrides/no writes, invalid input, missing/corrupt history and text/JSON output. Assertions pin observable messages, counts, lengths, coverage and exit codes.
- [x] Run `PYTHONDONTWRITEBYTECODE=1 python3 -B -Werror::ResourceWarning -m unittest tests.test_session_delta -v`. Expected: missing-command assertion failures before implementation.
- [x] Implement optional streaming consumers and the shared selector. Keep the first eligible message plus a bounded recent tail; when character-limited, share budget between the early message and newest context. One-message/one-character limits prefer the latest context. Counts refer to eligible conversation after the boundary, and include omitted characters from partially included messages.
- [x] Run focused tests. Expected: all pass; then run the complete suite with ResourceWarnings as errors. Expected: no failures or skips.
- [x] Document usage, JSON schema, boundary precision and failure behavior; update ticket 08 and progress with actual evidence.
- [x] Review the complete ticket diff independently; fix material findings with RED/GREEN regressions. Run the final suite and `git diff --check`, then commit the ticket if Git writes are authorized. Leave the branch local for ticket 09.

## Execution notes

- The user explicitly requested implementation of the existing ready ticket. Use its approved spec and execute inline without reopening product scope.
- Baseline: 132 tests pass with ResourceWarnings as errors; worktree clean at `60b87d0`.

## Final evidence (2026-11-09)

Ticket 08 is implemented. The final complete suite passes 157 tests with no skips
and ResourceWarnings as errors; the 25 dedicated tests also pass on macOS system
Python. Whitespace checks pass. One independent review found four Important
issues; all were reproduced RED and corrected GREEN before the final suite.
See `docs/testing/bounded-session-deltas.md` for review findings, tests and scope
decisions. The feature remains local; tickets 09–14 are not implemented here.
