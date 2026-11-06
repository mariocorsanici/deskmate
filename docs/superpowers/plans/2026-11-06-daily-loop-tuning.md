# Daily Loop Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement ready tickets 01–04: current remote state, a morning change report, stale Handoff disclosure, and bounded skill usage measurements.

**Architecture:** Keep morning planning and Checkpoint guidance in the existing shared skills. Add precise end events to the existing activity log and teach the token reader to close a skill at its earliest valid boundary. Preserve historical measurements and extension columns so the work can later be rebased onto the provider-neutral core.

**Tech Stack:** Existing Python standard library, zsh, Git, optional GitHub CLI, Markdown skills; no new dependencies.

**Spec:** `.scratch/daily-loop-tuning/spec.md` and issues `01`–`04` in `.scratch/daily-loop-tuning/issues/`.

## Global Constraints

- Tickets 01–04 are ready. Tickets 05–07 remain `needs-triage` until the next `/how-did-it-go`.
- Slack: deskmate never reads Slack unless the user asks.
- Replies keep following `config.json` `language`; repository documentation stays English.
- Work targets `feature/daily-loop-tuning`, based on `develop` at `70468e3`. Merge after `feature/codex-cli-support` has landed, rebasing first.
- Use focused commits, verify each ticket, update its acceptance checklist and push the feature branch at ticket boundaries when supported by the workspace.
- Native tooling created a managed detached worktree at the feature tip. Keep the task checkout unchanged; use native branch controls if branch publication is unavailable.
- Verification uses disposable local Git repositories, synthetic transcripts and temporary log files. No authenticated model requests or changes to installed personal data.
- At baseline this branch contains no automated tests (`unittest discover` reports zero tests); the 132 tests belong to the separate Codex branch.

## Review Focus

1. A failed fetch must be reported as unavailable freshness, never as proof that the remote has not changed; check in Task 1.
2. Repositories may have spaces, different default branches, no `origin/HEAD`, or unavailable `gh`; exercise in Task 2 without checking out or pulling files.
3. A Handoff title names tomorrow, not necessarily its creation time; use its recorded creation timestamp or a disclosed fallback in Task 3.
4. Two skill runs can begin and end within the same minute; use precise end timestamps and test repeated names, interleaving sessions and missing markers in Task 4.
5. Old logs, extension columns and concurrent hook writes must survive measurement updates; test locked, atomic CSV updates and append behavior in Task 4.

---

### Task 1: Remote file checks (ticket 01)

**Files:** Modify `skills/checkpoint/SKILL.md`; create `docs/testing/daily-loop-tuning.md`; update `.scratch/daily-loop-tuning/issues/01-checks-read-remote-state.md`.

**Interfaces:** Existing card Checks remain `- <label>: <command>`; continue using the card discovery implemented by the owning branch, without adding another card-location convention.

- [x] Reproduce the stale-file case with a local bare remote and two disposable clones: advance a ticket remotely, fetch in the older clone, and record the different local-file and `git show origin/<branch>:<path>` results.
- [x] Update Checkpoint guidance to distinguish remote ticket/PR state from local branches and uncommitted files. Include one labeled remote-file example and one labeled local-state example. Quote paths and use the actual configured integration/default branch rather than assuming `develop` everywhere.
- [x] Explain that a failed fetch or missing remote ref is an unavailable check, not a fresh remote result. Preserve the existing centralized fetch behavior.
- [x] Repeat the disposable Git check, including failed fetch, and document exact commands/results. Inspect the skill diff against all three acceptance criteria; update the ticket and commit the ticket boundary.

### Task 2: Remote changes before planning (ticket 02)

**Files:** Modify `skills/whats-on-today/SKILL.md`; extend `docs/testing/daily-loop-tuning.md`; update `.scratch/daily-loop-tuning/issues/02-what-changed-since-handoff.md`.

**Interfaces:** Consume active/paused cards and the existing Checks results. Reuse the repositories named by those checks and the work folder, deduplicated; do not hardcode a Claude card directory.

- [x] Record a baseline scenario: the Handoff still proposes a ticket that another author completed remotely; the old morning instructions do not require a change report before planning.
- [x] After Checks, inspect each active repository's remote integration/default branch since the Handoff timestamp. Show hash, author, subject and time; use repository identity (`git config user.name/user.email`) to mark known other authors, and disclose unknown identity. Determine the integration branch from card guidance first, then symbolic `origin/HEAD`; report ambiguity instead of inventing a branch.
- [x] When `gh` is available and authenticated, list PRs merged during the same window. Treat missing CLI/auth/network as partial coverage and preserve commit results. Reconcile work already completed with the Handoff before proposing the day.
- [x] Emit one combined empty-window line only when every inspected remote window is confirmed empty. Keep standby projects excluded. Report failed or ambiguous repositories separately.
- [x] Verify with disposable repositories covering another author, empty windows, a path containing spaces and a default branch other than `develop`; document missing-`gh` and failed-fetch behavior. Update ticket evidence and commit.

### Task 3: Handoff age and inactive days (ticket 03)

**Files:** Modify `skills/whats-on-today/SKILL.md` and `skills/call-it-a-day/SKILL.md`; extend `docs/testing/daily-loop-tuning.md`; update `.scratch/daily-loop-tuning/issues/03-stale-handoff.md`.

**Interfaces:** Add `Generated: <ISO-8601 timestamp with offset>` below the Handoff heading. Older files fall back to file modification time, explicitly labeled as estimated; the target date in the title is not creation time.

- [x] Record baseline cases for a Wednesday evening Handoff read Friday after an inactive Thursday, a normal adjacent day, and an older Handoff without creation metadata.
- [x] Have the evening skill record the creation timestamp. In the morning, compare local calendar dates and count complete intervening days with no Deskmate activity in `log.csv`; reminder-only rows do not count as work. Count calendar days, including weekends, and do not change the separate weekday retrospective rule.
- [x] With at least one inactive intervening day, open with the Handoff date, elapsed time, inactive-day count and the fact that current state comes from live Checks/remote changes. Use the Handoff for intent and preparation; unavailable live evidence remains explicitly unknown.
- [x] Document/replay cases with timezone offsets, midnight boundaries, reminder-only days, older files and unavailable timestamps/logs. Avoid presenting missing evidence as confirmed inactivity. Update the ticket and commit.

### Task 4: Skill completion boundaries and honest metrics (ticket 04)

**Files:** Modify `tools/log_event.sh`, `tools/token_usage.py`, all five `skills/*/SKILL.md`, and `README.md`; create `tests/test_token_usage.py` and `tests/test_activity_log.py`; extend `docs/testing/daily-loop-tuning.md`; update `.scratch/daily-loop-tuning/issues/04-accurate-skill-token-metrics.md`.

**Interfaces:** Preserve `log_event.sh <event> [detail] [session] [cwd]`. End events use `<skill>-end` with the matching start's session and folder. For these events only, an empty detail is populated with the current timezone-aware UTC ISO timestamp, with microseconds. Add `usage_scope` to measured rows: `end-marked` or `legacy-window`; preserve existing detail text, row order and unknown columns.

- [x] Write `unittest` scenarios for an end-marked run followed by unrelated work, a legacy run with no marker, consecutive skills, a repeated skill name in one minute, a next command before the marker, and an end marker from another session. Verify each currently missing behavior fails before implementation.
- [x] Add CSV integration tests proving a legacy header upgrades without losing rows or values, unknown/provider columns survive, end timestamps are precise, and append/recompute operations share the lock. Add malformed/missing-end cases that cannot falsely qualify as bounded measurements.
- [x] Update the logger under `.log.lock`: read the existing header, add `usage_scope` when needed, preserve extension fields and rows, and publish complete CSV replacements atomically. Existing start/reminder/event callers keep their argument contract. Use an isolated data-root override for subprocess tests, keeping the existing default.
- [x] Update `token_usage.py` to match start/end occurrences in log order per native session and skill. Normalize timestamps before comparison. Close each run at the earliest valid same-run end marker, next transcript command, or session end; never apply a late marker to an earlier occurrence. Only a valid marker that actually closes the window qualifies as `end-marked`; missing/invalid/late markers retain `legacy-window`. Marker rows receive no usage totals. Preserve native message-ID deduplication.
- [x] In each skill, capture its own logged start identity before work and add the end event as the final successful action. Interactive skills stay open while awaiting required replies. Early cancellation/unfinished work must not be reported as a completed skill. Do not select another session's most recent row when resolving identity.
- [x] Require `/how-did-it-go` to use only `end-marked` rows for claims about skill cost and say when that sample is unavailable. Document that metrics stop at the explicit marker, including its preceding model call; any final response after the marker lies outside that measurement. Preserve historical rows as visibly different windows.
- [x] Run `python3 -Werror::ResourceWarning -m unittest discover -s tests -v` and `git diff --check`; inspect the full diff against the ticket and Review Focus. Update README, acceptance evidence and commit.

## Completion and Integration

- [x] Verify the complete ready-ticket test suite and documented local Git scenarios; inspect every acceptance item in tickets 01–04.
- [x] Keep tickets 05–07 unchanged and record their pending retrospective decision.
- [x] Report automated evidence separately from instruction/document review; do not claim an authenticated Daily loop was exercised.
- [ ] Publish completed ticket checkpoints using the feature branch when workspace controls permit. Do not merge into `develop` or `main`: integration remains dependent on the Codex effort.

## Execution choice

Recommended: Native execution in this session, with one independent review of the completed change. The four tickets share existing skills, and three mainly alter their instructions; a separate implementer and reviewer for every ticket would add coordination without separating much work. The owner reviews this plan and chooses the execution method before implementation.

## Execution evidence (2026-11-06)

The owner approved Native execution and a final independent review. Tickets 01–04
were implemented in focused commits; 05–07 are unchanged. The final review found
one Important `$HOME` fetch regression, reproduced before its correction. Final
automated verification passes 19 tests; whitespace checks pass. Documented local
Git/calendar scenarios passed; authenticated provider behavior was not exercised.
This managed worktree stays available and integration into develop waits for Codex.

## Concurrent remote update

Before publication, the shared remote advanced from `b393220` to `9727969`.
Its two documentation commits were merged while preserving both the ticket 03
implementation evidence and the agenda follow-up comment. Tickets 05–07 are now
confirmed/ready and ticket 08 (morning login check) has been added; none of these
newly ready tickets is implemented by this approved 01–04 execution. References
to their pending triage above describe the original approved-plan snapshot.
The required Codex-before-develop integration order remains unchanged.
