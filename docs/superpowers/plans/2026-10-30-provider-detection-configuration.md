# Provider Detection and Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect compatible local Claude Code and Codex CLI Providers, report exclusions, and persist an explicit Default provider without hidden choices.

**Architecture:** Add a focused standard-library `tools/providers.py` command behind the stable `bin/deskmate` boundary. It probes each Provider with its version command, renders deterministic human output, and atomically updates the existing JSON configuration while preserving unrelated preferences.

**Tech Stack:** Python 3 standard library, `unittest`, command-level subprocess tests.

**Spec:** `.scratch/provider-neutral-cli/spec.md` and `.scratch/provider-neutral-cli/issues/02-provider-detection-and-configuration.md`

## Global Constraints

- Local terminal use on macOS with Claude Code, Codex CLI, or both.
- Runtime uses only the Python standard library.
- Tests use an isolated home, isolated Deskmate data, and synthetic Provider executables.
- Existing configuration keys are preserved.
- Unsupported future configuration schemas stop before mutation.

## Review Focus

- A same-named executable whose version probe fails must be excluded with the failure reason.
- A version probe that hangs must time out and leave other Provider detection usable.
- Both compatible Providers in non-interactive mode must not choose a Default provider implicitly.
- Invalid interactive/default input must not mutate existing configuration.
- A malformed or future-schema configuration must remain byte-for-byte unchanged.

---

### Task 1: Provider capability detection

**Files:**
- Create: `tools/providers.py`
- Modify: `bin/deskmate`
- Modify: `tests/test_deskmate_cli.py`

**Interfaces:**
- Consumes: `PATH`, `DESKMATE_DATA_DIR`, and Provider `--version` output.
- Produces: `deskmate providers`, returning one deterministic included/excluded line per Provider and a nonzero status only when no compatible Provider exists.

- [ ] Add command-level tests using temporary executable fixtures for Claude-only, Codex-only, both compatible, one incompatible, neither present, unrecognized output, nonzero exit, and timeout.
- [ ] Run the focused tests and verify they fail because `providers` is not yet a command.
- [ ] Implement Provider definitions and bounded version probes in `tools/providers.py`, then delegate `providers` from `bin/deskmate`.
- [ ] Run the focused tests and the complete suite; keep output deterministic in both human and top-level JSON modes.
- [ ] Commit the independently working detection command.

### Task 2: Explicit Provider configuration

**Files:**
- Modify: `tools/providers.py`
- Modify: `bin/deskmate`
- Modify: `tests/test_deskmate_cli.py`

**Interfaces:**
- Consumes: `deskmate configure [--non-interactive] [--default-provider claude|codex]` and current `data/config.json`.
- Produces: configuration schema version `1`, `providers.installed` in canonical order, and `providers.default`, written atomically while preserving unrelated keys.

- [ ] Add tests for automatic single-Provider selection, interactive dual-Provider selection, explicit dual-Provider selection, refusal of hidden non-interactive selection, unavailable defaults, and no compatible Providers.
- [ ] Run the focused tests and verify the missing behavior fails for the expected reason.
- [ ] Implement argument parsing, explicit selection rules, and concise success/failure output.
- [ ] Run focused tests and the complete suite.
- [ ] Commit the configuration behavior.

### Task 3: Schema safety and ticket completion

**Files:**
- Modify: `tools/providers.py`
- Modify: `tests/test_deskmate_cli.py`
- Modify: `.scratch/provider-neutral-cli/issues/02-provider-detection-and-configuration.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: absent, legacy unversioned, current version `1`, malformed, and unsupported future configuration documents.
- Produces: an atomic current-schema document or an actionable refusal with the original file unchanged.

- [ ] Add tests proving legacy migration preserves preferences, repeat configuration is stable, and malformed/future schemas are rejected before mutation.
- [ ] Run the focused tests and verify the new schema cases fail for the expected reasons.
- [ ] Implement validated reads and same-directory atomic replacement using `os.replace`.
- [ ] Document the two new commands and mark every ticket 02 acceptance criterion complete with a short implementation comment.
- [ ] Run the complete test suite and command help checks.
- [ ] Commit the completed ticket.

