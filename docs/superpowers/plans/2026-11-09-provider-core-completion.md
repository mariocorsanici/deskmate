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

- C13 resumed 2026-11-09, owner request "Iniziamo ticket C13", session `/root`.
  Execute Task 4 only, inline, with TDD and one independent final review.
  Prepare in `/private/tmp/deskmate-c13` because the existing linked worktree
  is outside the sandbox writable roots; apply the verified patch to the
  existing feature worktree with filesystem authorization at the ticket boundary.
  Baseline source: `e375535`. No actual user installation or native model request.

### C13 task detail

Interfaces: `deskmate setup [--provider claude|codex]...
[--default-provider claude|codex] [--non-interactive] [--project PATH]...
[--name NAME] [--language LANGUAGE]`; `deskmate remove [--non-interactive]
[--purge-data]`. `install.sh` forwards to these commands.

- [x] RED: public command tests cover detection/default/override matrix, portable
  skill links and actual shell discovery, unrelated hooks/preferences, repeated
  setup, config/cards/log backups and future schema rejection without mutation.
- [x] Implement `tools/installation.py` to preflight and stage using existing
  adapters and migration readers. Resolve Claude project identity from explicit
  folders, card folder paths or session indexes; stop with `--project` guidance
  when uncertain, without guessing a path from its lossy encoded key.
- [x] RED then GREEN: journaled atomic per-file publication in
  `tools/install_transaction.py`, rollback and interrupted-transaction recovery,
  permission/collision failure and concurrent-change refusal. Use existing card,
  log and native hook locks while publishing to preserve concurrent writers.
- [x] RED then GREEN: logging verification and trust guidance, reminders through
  fake launchctl, shell path exposure, owned removal, default data preservation,
  interactive default-no/exact DELETE and explicit unattended purge.
- [x] Full suite and system Python focused suite; independent review/fixes with
  regressions; document evidence; apply to existing feature worktree and commit
  C13 only. Record native acceptance as pending.

- C13 implementation: shared setup/remove facade, staged adapters, reusable
  journaled file/link publication, verified runtime service rollback, private
  backups, normalized paths and preserved unrelated state. Common setup skill
  scenario observed baseline failures then passed with the shared replacement.
- C13 review: one independent review, six Important findings reproduced RED
  and fixed GREEN (custom Codex configuration, service-only journals, failed
  service restoration, configuration lost-update race, tilde-root schema bypass,
  unsafe repository-ancestor purge). Setup Codex metadata contract also fixed
  after the full suite exposed the missing file.
- C13 decision: only zsh/bash receive managed PATH entries; linked/special shell
  files require explicit manual PATH guidance rather than being replaced. A
  project with unresolved legacy path identity stops setup with --project
  guidance. Wrong inference would risk migrating the wrong durable card.
- C13 deferred Minor: Provider detection output is printed before explicit
  subset selection, so its included/excluded wording describes detection.
  Actual installed configuration/integrations and verification reflect the
  override; ambiguous wording can be clarified separately.

- C13 verification: 31/31 focused tests; 224/224 full-suite tests on Python
  3.14.6; 31/31 installation scenarios on Python 3.9.6, ResourceWarnings as
  errors. All six Important findings fixed with observed RED/GREEN regressions;
  review outcome and the deferred wording Minor are in docs/testing/installation.md.
  Keep this feature branch/worktree for C11 and C14; no integration before C14.

- Stop at the C13 local ticket commit. Next scheduled ticket is C11; C14 remains blocked by C11. No push, merge, personal installation or native request authorized in this boundary.


### C11 task detail — resumed 2026-11-10

Owner authorized updating the shared tracker and starting C11. Reuse Task 5,
inline with TDD, from clean `3b0c510`. Baseline 224/224 passed. Work in
`/private/tmp/deskmate-c11-a6hra4n5` until the verified patch can be applied to
the existing feature worktree with filesystem authorization. C14, native model
requests, personal installation, push and merge remain outside this ticket.

Interfaces: `deskmate retrospective --since DATE [--select PROVIDER:ID]...
[--format text|json]`; alternatively `--deepen PROVIDER:ID` with an explicit
`--max-messages N` and/or `--max-characters N`. Selection replaces recommendations;
repeating `--select` adds sessions, omitting it reads no deltas. Deepening accepts
one session and overrides only this command's limits.

Design: one `tools/retrospective.py` builds a read-only durable/metadata view,
then optionally reads chosen deltas through existing adapters. Reuse shared card
validation, CSV reading, cached raw metrics and configured delta limits. Avoid
`metrics.report`, which refreshes native usage by scanning transcripts; initial
metrics explicitly identify metadata/cached snapshot provenance. Keep all
candidates and Provider identities visible, while recommending at most five
with reasons from logged activity, card ownership, incomplete metadata and recency.
The skill owns user confirmation and the conversation, using this command rather
than introducing a persistent selection store or an interactive CLI wizard.
Existing C08 owns bounded reads; this ticket adds orchestration and scenarios.

- [x] Public RED: nine synthetic CLI scenarios fail because the retrospective
  command is missing (one rejection-only test already passes and is not RED proof).
- [x] Add durable/metadata collection, reasoned recommendations and isolated
  Provider metrics. Guard the initial phase against conversation reader entry.
- [x] Add validated explicit selection and one-session deepening, configured
  limits, per-session degradation and read-only CLI routing.
- [x] Apply old/new skill to synthetic scenarios; update instructions for the
  selection pause, durable evidence, separated raw metrics and bounded deepening.
- [x] Full suite, focused suite on system Python, independent review and fixes,
  ticket/evidence/tracker updates, apply to existing feature worktree and commit.

- C11 instruction scenario: baseline read eight unselected Claude transcripts;
  revised flow listed all 11 Provider-owned candidates and stopped before reads.
  Chosen Codex-only selection and 3/40 one-off deepening worked; next read
  reverted to configured 2/20 without a configuration change.
- C11 review fix pass: malformed cached metadata now degrades its record; the
  experiment lens uses saved evidence to avoid unselected transcript scans.
  Alternative date forms are explicitly rejected to prevent silent evidence loss.
  These cases were observed RED and then GREEN; no review findings deferred.
- C11 choice: native/cached counters are labelled by Provider, source and snapshot
  time; saved experiment samples can support decisions, unavailable measurements
  cannot. Standalone session-stats remains available outside this retrospective.

- C11 final verification: 239/239 full suite on Python 3.14.6; 15/15 focused
  retrospective scenarios on Python 3.9.6, ResourceWarnings as errors, no skips.
  All acceptance checkboxes and evidence updated; apply/verify/commit C11 only.

### C14 task detail — resumed 2026-11-10

Owner request "Iniziamo il task C14", session `/root`, baseline `b10d282`.
Execute Task 6 only in a disposable copy, then apply to the existing feature
worktree. The native-request hold remains; incomplete native acceptance prevents
closing C14 or merging. No personal installation, push or merge is included.

- [x] Apply baseline morning/evening/Checkpoint/study scenarios; reproduce
  Claude-only routing, premature history reads, wrong data root and rating owner.
- [x] Replace morning launch with `work-session`, evening collection with
  Provider-owned metadata and individually bounded deltas, and native skill
  syntax/data-root/Checkpoint-rating guidance in the shared sources.
- [x] Remove obsolete shell entry points and the superseded Claude session
  summarizer; remove `open-session`. Keep exact legacy hook identifiers only
  for setup/removal ownership matching, never dispatch.
- [x] RED/GREEN default session discovery: both Providers, no messages; explicit
  message reads carry bounded delta coverage, omissions and truncation. A listed
  session without matching card ownership does not get a misleading resume.
- [x] Synthetic Daily loops exercise setup, real installed hook commands,
  routing/confirmation, Checkpoint, Checks, selected retrospective, evening
  evidence and preserving removal for singles and both defaults. Switch and
  consume run both directions through fake native tools and real public commands.
- [x] Promote the specification to `docs/provider-neutral-cli.md`; final user
  commands in README; tracker disposition and native runbook in
  `docs/testing/daily-loop.md`.
- [x] Full/system checks and independent whole-feature review/fixes: 248/248
  on Python 3.14.6; 27/27 Daily-loop/transfer scenarios on Python 3.9.6.
- [x] Applied to the existing feature worktree; destination full suite passed before the local synthetic C14 checkpoint commit.
- [ ] Run authenticated native acceptance after the owner lifts the hold.

Baseline verification: 239 tests ran; a pre-existing PTY harness race reported
one failure despite printed `Switch confirmed`. The isolated affected transfer
expiry scenario passed on rerun. Investigation found EOF can arrive before
`poll()` observes exit; the harness now waits boundedly for exit before failing.
No production switch behavior changed for that race.

C14 independent whole-feature review found two Important privacy/lifecycle issues:
recognized multiline credentials retained their body after marker-only redaction,
and abrupt transfer writes could survive expiry indefinitely. Both reproduced
RED before the fix pass. Ambiguous credential extents now block; transfer creation
uses private reserved staging plus atomic publication, and expiry preserves live
writers and unrelated files. Additional lock-removal regression failed as expected.

Review disposition: authenticated native acceptance remains on hold; exhaustive
secret detection is not guaranteed; structured Check allowlisting and non-macOS
support remain deferred. Evidence and practical limitations are recorded in
`docs/testing/daily-loop.md`.
