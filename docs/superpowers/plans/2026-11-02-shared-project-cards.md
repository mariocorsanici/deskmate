# Shared Project Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** One safe, shared Project card per canonical project across Providers.
**Architecture:** A standard-library storage module behind `deskmate card` owns identity, strict metadata, locks, atomic updates and migration. Skills compose Markdown and use revision checks.
**Tech Stack:** Python standard library, unittest, Markdown.
**Spec:** docs/superpowers/specs/2026-10-30-shared-project-cards-design.md

## Global Constraints

- Python standard library only.
- All externally visible behavior is exercised through `bin/deskmate` with an isolated home and `DESKMATE_DATA_DIR`.
- Reject unsupported future schemas before any mutation.
- Preserve Claude access with a symlink and recoverable migration backups.

## Review Focus

- Missing/non-directory project paths must create no storage.
- Malformed metadata including duplicate JSON keys must not be silently accepted.
- Unexpected or dangling symlinks must not redirect writes or lose legacy content.
- Interrupted migration must resume without duplicate backups or revision increments.
- Concurrent writers must serialize and return status 3 with the current document.

### Task 1: Shared card command and storage

**Files:** create `tools/project_cards.py`, `tests/test_project_cards.py`; modify `bin/deskmate`.
**Interfaces:** CLI `card locate PROJECT`, `card list`, `card write PROJECT --expected-revision N --provider claude|codex --session-id ID --from FILE`.

- [x] Add command tests for canonical path identity, same-name isolation, creation, metadata, revision conflicts, invalid candidates/current documents, list ordering, future schemas and invalid project paths.
- [x] Run `python3 -m unittest tests.test_project_cards -v`; expect unknown-command failures before implementation.
- [x] Implement canonical identity, restricted frontmatter JSON validation, stable flock, same-directory temporary files and atomic replacement. Locate outputs JSON `{path, metadata}`; list outputs one path per line. Metadata is authoritative on writes.
- [x] Run targeted tests; expect success.

### Task 2: Migration and concurrency

**Files:** extend the same module and command tests.
**Interfaces:** CLI `card migrate PROJECT`; uses Task 1 identity, validation and locking.

- [x] Add tests for legacy ownership extraction, exact backups, repeated migration, partial migration, differing content, unexpected symlinks, parallel writers and held locks; run them and observe failures.
- [x] Implement content-addressed exclusive backups, lossless frontmatter preservation, atomic symlink replacement, safe repair and refusal to create parallel writable cards.
- [x] Run targeted tests; expect success.

### Task 3: Shared-card callers and documentation

**Files:** modify `tools/check.py`, `skills/{checkpoint,call-it-a-day,whats-on-today}/SKILL.md`, `README.md`, ticket 03.
**Interfaces:** Checks discover the same shared data root as card storage; skills use locate/list/write instead of Claude paths.

- [x] Add integration tests for shared discovery and standby filtering; run and observe failures.
- [x] Update discovery, skill instructions and README, documenting manual-edit concurrency limits and migration command.
- [x] Run `python3 -m unittest discover -v` and `git diff --check`; expect all tests passing and no whitespace errors.
- [x] Review the ticket against the diff; update acceptance checklist only after verification. Keep the multi-ticket feature on its branch.

## Execution record

Native execution in the existing feature worktree; no merge or release. Baseline: 36 tests pass. User approved the existing design and implementation on 2026-11-02.

Completed all three tasks; targeted RED runs preceded implementation. Full suite:
53 tests pass. Independent review covered the shared-card protocol and skill
application scenario; all reported issues have regression tests and fixes.

Rulings: locate emits JSON `{path, metadata}`, list emits paths one per line,
and no-card metadata is null. Backups use exclusive hard-link publication of
a flushed private temporary file to avoid truncated content-addressed backups.
No merge, push, installation or real-user migration was performed.
