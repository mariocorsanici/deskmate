# Checkpoint Timestamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close C14-CODEX-01 by preventing incompatible Checkpoint timestamps from being published.

**Architecture:** Share parsing in `tools/checkpoints.py`; use it from the card writer and Session delta reader. The skill obtains the time from the system in UTC.

**Tech Stack:** Python standard library, unittest, macOS system Python 3.9 compatibility.

**Spec:** `docs/superpowers/specs/2026-11-11-checkpoint-timestamp-design.md`

## Global Constraints

- Existing ISO timestamps and legacy local minute timestamps remain readable.
- Invalid new candidates return exit 2 without replacing a card or increasing its revision.
- Cards without a Checkpoint remain writable; existing ownership, locking and revision-conflict behavior remains.
- Native requests remain Codex only; no push or merge.

## Review Focus

- Invalid timestamp during initial publication creates no storage.
- Invalid timestamp during update preserves the previous bytes, revision and legacy link.
- Old manually edited invalid cards degrade with bounded context and an explicit warning.
- Numeric offsets, UTC Z and legacy local minutes retain the same delta boundary.
- Cards without a Checkpoint and mismatched-session checkpoints preserve existing behavior.

## Task 1: Shared parsing, publication validation and skill guidance

**Files:** create `tools/checkpoints.py`; modify `tools/project_cards.py`, `tools/session_delta.py`, `skills/checkpoint/SKILL.md`, `tests/test_project_cards.py`, `tests/test_session_delta.py`, `README.md` and the C14 evidence.

**Interfaces:** `instant(value, *, require_zone=False, native=False)` preserves the current contract; `checkpoint_boundary(text, *, session_id=None)` returns the existing timestamp/source/precision mapping or None and rejects invalid checkpoint timestamps.

- [x] Add public-command regressions for initial/update rejection of CET, malformed dates/lines and accepted ISO roundtrips; capture RED. Add legacy invalid-card fallback coverage.
- [x] Extract shared parsing, validate before mutation, update the reader; keep non-checkpoint cards and ownership semantics.
- [x] Update the skill to obtain a UTC ISO timestamp from Python; use the existing card-write error handling. Baseline native skill failure is recorded in `c14-codex-native-2026-11-11.json`.
- [x] Run focused tests on Python 3.14 and 3.9, then the full suite with ResourceWarnings treated as errors.
- [x] Review the focused change with one fresh reviewer, apply any material findings using RED/GREEN regressions.
- [x] Apply to the existing feature worktree, verify the destination, and make a focused local commit.
- [x] Run a fresh native Codex Checkpoint then selected retrospective without timestamp hints; preserve actual outputs and update the finding disposition.

## Execution ledger

- Task 1 started from `24b431f`, in a temporary source copy because the existing feature worktree is outside writable roots. Inline execution is authorized by the owner's “ok, vai pure” after the concrete solution.

- RED: new initial/update/malformed-line public regressions observed failing because incompatible timestamps were accepted. Initial implementation exposed the CLI's Python -I sibling-import constraint; existing tests caught it, and the standard explicit tools-directory path was restored.
- GREEN: 47/47 card and delta tests on Python 3.14.6 (8.647s), and 47/47 on Python 3.9.6 (24.795s), ResourceWarnings as errors.
- Independent review: approved; no Critical, Important or Minor findings. Reviewer independently passed 47/47 on both Python versions and checked CRLF, missing/malformed Checkpoints and mismatched IDs.
- Final: Ruling: older feature behavior outside the timestamp change retains its earlier C14 review and acceptance status; this focused fix does not close unexecuted Claude/cross-Provider groups. Native adherence and full-suite execution set aside by the reviewer are independently verified by the implementer below.

- Final full suites: preparation 253/253 (98.537s); existing feature destination 253/253 (104.827s), ResourceWarnings as errors.
- Native regression: fresh session `01a1cb36-325e-7de3-99e9-2952c94610bd`, no formatting hints; system-generated UTC timestamp saved first attempt and selected retrospective recognized boundary without warnings. Process exit 0; auth reference removed.
- Final: Ruling: separate post-exit cold read-only SQLite access can degrade when WAL/SHM files are absent; recorded as C14-CODEX-02 for triage instead of expanding the timestamp fix. Cost: historical deltas can remain unavailable until the SQLite lifecycle issue is addressed. Live native regression passed before any diagnostic warm-up.

- Task 1: complete; focused implementation and independent review verified, full suite 253/253 in both preparation and destination, fresh native regression passed. Local checkpoint commit contains the implementation and evidence; C14-CODEX-02 remains a separate follow-up.
