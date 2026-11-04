# Provider routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Complete ticket 07: select the correct Provider, resume or explicitly create a Work session, and update ownership only from confirmed native identity.

**Architecture:** Add one routing module behind `deskmate work-session`, reusing provider detection/configuration, shared Project cards and native adapters. Keep launch attempts in a per-project journal correlated to native hooks; atomically bind confirmed native ownership with a revision check. Preserve the existing low-level commands until later ticket migrations.

**Tech Stack:** Python standard library, unittest, macOS/iTerm adapter boundary.

**Spec:** `.scratch/provider-neutral-cli/issues/07-provider-routing.md`, `.scratch/provider-neutral-cli/spec.md`, and `docs/superpowers/specs/2026-11-04-provider-routing-design.md`.

## Global Constraints

- "A normal resume uses the Provider recorded by the Project card."
- "The command produces concise human-readable output by default and offers stable JSON output for skills, hooks and tests."
- "A Provider switch is a new Work session built from the Project card, current Checks and an optional Session delta. It is not a cross-provider resume."
- "Project cards remain Markdown with a restricted, validated metadata header containing schema version, revision and session ownership fields."
- "Card writes use a lock and atomic replacement. Revision checks detect stale writers, which reread rather than silently overwrite."
- "An unsupported future schema stops before any mutation."
- Use the existing feature worktree and `feature/codex-cli-support`; do not merge the incomplete multi-ticket feature into develop/main.
- Authenticated manual checks are postponed by the owner. No real Claude/Codex launch, model request, personal configuration mutation or transcript access during implementation/validation.

## Review Focus

- A recorded session is absent or belongs to another canonical folder: require explicit recovery rather than launching or silently changing Provider (Task 1).
- Invalid/missing Provider configuration or unsupported journal/card schema: fail before durable writes or terminal launch (Tasks 1–2).
- Terminal submission fails, times out or receives an early native hook: preserve old ownership and retain truthful attempt evidence (Tasks 2–3).
- Two attempts race, or a Checkpoint changes the card while launch is pending: stale confirmation cannot overwrite newer state (Tasks 2–3).
- Unrelated, duplicated or malformed hook payloads and missing hook approval: never invent ownership; report pending/degraded confirmation and preserve unrelated logging (Task 3).

---

## File structure and command contract

- Create `tools/work_sessions.py`: routing, journal transitions and CLI rendering.
- Modify `bin/deskmate`: register the stable `work-session` command/help.
- Modify `tools/project_cards.py`: internal revision-checked metadata-only ownership operation, preserving existing body/frontmatter and using the existing project lock.
- Modify both Provider adapters: metadata-only resume eligibility for a canonical folder; optional `launch_id` correlation environment in safely quoted native launch commands.
- Modify `tools/hook_event.py`: forward correlated native lifecycle/prompt evidence to the routing module while preserving activity logging.
- Modify Claude integration to install SessionStart/SessionEnd hooks idempotently, preserving personal hooks. Codex already installs them.
- Create `tests/test_work_sessions.py`: public-command acceptance/regressions with isolated synthetic stores and fake executables; extend adapter/hook tests where their public behavior changes.
- Update `README.md`, ticket 07 and the provider progress note after validation.

Command: `deskmate [--json] work-session --folder PATH [--new [--provider claude|codex]] [--title TEXT] [--prompt TEXT] [--dry-run]`.

Human output states resume/new/pending/refused/error and explains recovery. JSON retains the existing envelope and returns a structured inner result with `schema_version`, `status`, `mode`, `provider`, `session_id`, `reason`, `warnings`, `card_revision` and `launch_id` where applicable. Exit 0 means a valid plan or successful submission, 1 unavailable/failed launch, 2 invalid input/configuration, 3 revision conflict and 4 explicit new-session choice required. `--dry-run` never writes state or opens a terminal; `--provider` without `--new` is rejected.

### Task 1: Predictable routing and explicit recovery

**Interfaces:** `plan_session(folder: str, *, new: bool = False, provider: str | None = None) -> dict` in `tools/work_sessions.py`; `resume_available(session_id: str, folder: str | None = None) -> bool` in each adapter. Preserve the existing Codex one-argument use.

- [x] Add public tests named `test_recorded_provider_overrides_default`, `test_unowned_project_uses_default`, `test_missing_session_requires_explicit_new`, `test_missing_provider_never_falls_back`, `test_wrong_folder_refuses_resume`, and `test_dry_run_and_invalid_configuration_do_not_mutate`. Assert both Providers, canonical aliases, unchanged card bytes, no launch/journal writes and distinct human/JSON outcomes. An explicit `--new --provider codex` resolves a lost Claude session; an ordinary invocation returns exit 4 and no launch.
- [x] Run `python3 -Werror::ResourceWarning -m unittest tests.test_work_sessions -v`; observe the expected missing-command failures.
- [x] Implement the public command and read-only planner. Validate configured installed/default Providers, fresh executable availability and card metadata; do not infer native resumability from usage/message parsing status. Reject unknown sessions and folder mismatch using native metadata; never read conversation content to route.
- [x] Run the focused tests and existing adapter/CLI tests. Expected: routing cases pass, existing low-level behavior preserved.
- [x] Commit the routing behavior after checks, if Git writes are authorized.

### Task 2: Launch journal and revision-safe ownership

**Interfaces:** `start_session(plan: dict, *, title: str | None = None, prompt: str | None = None) -> dict` and `record_native_event(provider: str, payload: dict, launch_id: str | None) -> dict | None` in `tools/work_sessions.py`. The journal is `data/projects/<project-key>/work-sessions.json`, schema 1, with independent attempt records containing correlation ID, provider, expected revision, mode, native identity and transition state.

- [x] Add failing public scenarios `test_launch_failure_preserves_owner`, `test_submitted_new_session_has_no_invented_id`, `test_stale_confirmation_preserves_checkpoint`, `test_competing_attempts_remain_visible`, and `test_future_journal_schema_stops_before_launch`. Assert failed launch leaves original card byte-for-byte intact; submission alone stays pending; no pending token is written as a native session ID.
- [x] Run the focused module and observe failures for missing journal/ownership behavior.
- [x] Add a metadata-only internal card operation using the existing lock, revision validation, metadata renderer and atomic writer. Preserve Markdown; when a confirmed new session has no card, create minimal honest Status/Checks content without claiming a Checkpoint happened. Keep schema 1 ownership pairs valid.
- [x] Implement prepared/submitted/confirmed/failed/conflict attempt transitions. Persist an attempt before terminal launch, release locks during external operations, and record uncertainty rather than silently retrying. Hook evidence received while prepared waits for successful submission before ownership changes. Cancellation/errors never commit ownership. A journal/card recovery path must make partial atomic-write failures explicit rather than erase newer content.
- [x] Run focused tests. Expected: safe ownership and competing-attempt cases pass; attempts remain inspectable for ticket 09.
- [x] Commit the ownership/journal behavior after checks, if Git writes are authorized.

### Task 3: Native correlation, integration validation and ticket evidence

**Interfaces:** Extend `adapter_claude.launch(...)` and `adapter_codex.launch(...)` with optional keyword `launch_id: str | None = None`; export a validated `DESKMATE_LAUNCH_ID` only in the launched native command. Hook handling calls `record_native_event` for correlated SessionStart, first UserPromptSubmit, and SessionEnd events. Events without a matching token never steal card ownership.

- [x] Add failing scenarios `test_confirmed_native_identity_updates_owner`, `test_early_hook_waits_for_successful_submission`, `test_unrelated_and_duplicate_hooks_cannot_steal_owner`, `test_missing_hooks_leave_pending_status`, and `test_session_end_preserves_attempt_history`. Cover both Providers, matching folder/provider/token, ID validation, replay after a newer Checkpoint, and shell-sensitive paths/titles/prompts. Assert existing skill/usage activity remains unchanged.
- [x] Run the focused tests and observe the expected missing-correlation failures.
- [x] Wire token delivery, lifecycle hooks and native confirmation. Preserve personal configuration, explicit approval/trust instructions, and hook JSON output. Report pending native confirmation separately from launch submission. Include launch-attempt history in structured results where it identifies possible overlap; leave actual switch confirmation to ticket 09.
- [x] Run `python3 -Werror::ResourceWarning -m unittest discover -s tests -q` and `git diff --check`. Expected: all tests pass, no skips introduced, no whitespace errors. Tests must use fake executables and isolated HOME/CODEX_HOME/data only.
- [ ] Review the complete ticket diff against its seven acceptance criteria and the five Review Focus cases. Fix concrete gaps and rerun the affected checks.
- [x] Document command examples and recovery/pending outcomes; mark ticket implementation complete with actual automated evidence. Update the progress note to distinguish 01–07 completion from 08–14 remaining work, and record manual checks as postponed rather than passed.
- [x] Commit the final ticket boundary if authorized; do not push or merge unless separately within the active task scope.

## Execution notes (2026-11-04)

Task 1: six new routing tests observed failing on the missing command, then 78
routing/adapter/CLI tests passed. Commit `939bdec`.
Task 2: five journal/ownership cases observed failing, then the full 116-test
suite passed with ResourceWarnings as errors. Commit `c7f8454`.
The minimal correlated-hook entry point was wired during Task 2 so stale ownership
and conflicting attempts were tested at the public command boundary; Task 3 adds
actual token propagation and lifecycle integration. This changes task sequencing,
not the agreed behavior. Task 3's first correlation/integration run failed before
token delivery, lifecycle hook installation and preflight title validation were
implemented. Existing manual hook cases already covered by Task 2 passed.

macOS temporary paths may spell the same location through /var or /private/var;
assertions compare resolved identities, consistent with Project identity rules.

Final task verification before independent review: 128 tests passed, no skips, ResourceWarnings as errors.
