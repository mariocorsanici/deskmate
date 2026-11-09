# Provider-neutral core completion plan

Execute inline with `superpowers:executing-plans` and TDD. This continues the
owner-approved three-branch delivery plan's point 1 on the existing Codex worktree.

Spec: `.scratch/provider-neutral-cli/spec.md`, tickets 09–14. Baseline: `48feaf6`,
157 recorded tests. The shared delivery tracker is in the main checkout at
`docs/superpowers/plans/2026-11-09-development-tracker.md`.

## Constraints and review focus

Python stdlib only; fake native tools, isolated homes and data in automated tests.
No real credential reads, destructive purge or installed configuration changes.
Native authenticated acceptance stays pending until the owner lifts its recorded
quota hold. Do not merge before complete C14 acceptance. Preserve card revisions,
confirmed native ownership, metadata-only discovery and separated Provider usage.

Review focus: cancellation/stale cards during a switch; path-only consent-bound
bundles and content-free audit; unexpected redaction formats and orphan cleanup;
installation rollback across config/cards/logs/native hooks; retrospective reading
only explicitly selected deltas; final native acceptance never inferred from fakes.

### Task 1 — C09: degradable switch

Add `deskmate switch --folder PATH --to claude|codex [--preview]`. Shared switch
planning consumes the current Project card, current Checks and existing launch
journal; launch always calls `work_sessions.start_session` with mode=new and no
source native session ID. Source availability never prevents target continuation.
Use an interactive overlap warning and confirmation, preserving ownership on
cancellation/failure. Context is passed via a private file path, never body text
in arguments. Initial C09 context is card-plus-Checks; C10 adds protected deltas.

- [x] Public tests RED: both switch directions, missing source/transcript, live
  check results, overlap warning, cancellation, no piped/flag consent bypass,
  failed target launch and preserved native ownership protocol.
- [x] Implement `tools/provider_switch.py`; route it in `bin/deskmate`.
- [x] Focused GREEN, full suite, ticket/progress/tracker update and focused commit.

### Task 2 — C10: protected context transfer

Add `tools/transfers.py` for recursive local redaction, preview manifest, uncertain
finding refusal, explicit interactive consent, mode-0600 bundles under a private
directory, target-owned read-and-delete and one-hour orphan cleanup. Switch plans
add the bounded `read_delta` result. Public `transfer-read` consumes only managed,
matching-target bundles; bundle content never enters audit records or argv.

- [x] Public RED tests: canaries, redaction counts, uncertain findings, no bypass,
  permissions, path-only launch, wrong-target/symlink refusal, consume/expiry,
  no unrelated file removal, stale card and content-free audit.
- [x] Implement and exercise real file/CLI boundaries; GREEN, full suite and commit.

### Task 3 — C12: dual-Provider reminders

Render native invocation forms from configured installed/default Providers while
keeping existing channels, language and response logging. No real notifications
in tests. RED tests pin each single Provider, both defaults, localized text,
calendar escaping and recorded Provider identity; then GREEN/full suite/commit.

- [x] Provider matrix, ordering, localization/calendar, response/snooze/dry-run
  scenarios observed RED and then GREEN with isolated configuration/fake commands.
- [x] Independent review completed; displayed-Provider attribution race fixed
  with RED/GREEN regression. Restore concise CSV errors and retain both invocation
  arguments with additional RED/GREEN regressions.
- [x] Full suite 193/193 on Python 3.14.6; reminder suite 13/13 on system Python
  3.9.6. See `docs/testing/provider-reminders.md`.

### Task 4 — C13: installation, migration and removal

Add stable setup/remove operations with provider overrides, explicit default for
noninteractive dual installs, stable command link and native integration verification.
Stage/preflight migrations with backups and recoverable publication; reject newer
schemas before mutation. Reuse adapters and card/log migration APIs. Removal keeps
data by default; purge requires separate interactive exact DELETE confirmation.
RED tests operate in temporary homes and validate preservation, idempotency,
rollback/failure visibility and install/removal ownership. GREEN/full suite/commit.

### Task 5 — C11: progressive retrospective

Provide a metadata/durable-state candidate view with all Provider-owned sessions,
at most five reasoned recommendations, user-editable selection, selected bounded
deltas and per-session one-off deepening. Initial view never reads conversation.
Keep native raw metrics separate and degrade per session. Public RED tests,
implementation and instruction scenario checks, GREEN/full suite/commit.

### Task 6 — C14: clean cut and full acceptance

Move all skills/hooks/reminders/docs to the final command and Provider-neutral
ownership/discovery rules. Remove obsolete Claude-only entry points with verified
reference checks; promote durable specs/tracker decisions. Validate complete
synthetic Daily loops for Claude-only, Codex-only and dual setups; independently
review the feature and fix material findings with regressions. Complete the
authorized native acceptance matrix before marking C14 complete or merging.

If native acceptance remains unavailable, finish all independent implementation
and automated checks, record the concrete remaining check and preserve the branch.

## Execution ledger

- 2026-11-09: owner requested autonomous execution of point 1. C09 started in the
  existing worktree; native quota-hold clarification asked while synthetic work proceeds.

- C09: six acceptance tests observed RED, then GREEN. Full suite 163/163 passed with ResourceWarnings as errors; no skipped/native checks claimed.

- C10: 180/180 final full-suite tests passed with no skips and ResourceWarnings as errors; 23 focused tests also passed on system Python. Independent review found four Important issues, reproduced RED and fixed GREEN; one generic transcript warning remains Minor. See `docs/testing/provider-switches.md`.
- Stop directive: the owner requested stopping at the next committed/pushed ticket while C10 was underway. Commit C10 and stop; tasks C12, C13, C11 and C14 remain unstarted. No push, merge, real model request or installed-user-data operation is included in this boundary.

- C12 resumed: on 2026-11-09 the owner requested the next scheduled ticket only;
  session `/root` continued Task 3 on the existing branch from `8e34b5a`.
- C12: 13 reminder tests passed, full suite 193/193 passed, and all 13 reminder
  tests passed on system Python 3.9.6. One independent ticket review completed;
  the attribution race and error-reporting regression were fixed with RED/GREEN
  regressions. Native desktop/calendar/model acceptance is still pending.
- C12 decision: a desktop response is attributed to the Default provider displayed
  in the alert, without a native session identity; this is not proof of skill use.
  Legacy configurations without Provider settings remain Claude-only until setup
  migration. Both choices preserve existing data meaning; interpreting reminder
  rows as actual Provider usage would misattribute metrics.
- Stop after the C12 ticket commit. C13 is next; no push, merge, installation or
  authenticated native request is included in this task.
