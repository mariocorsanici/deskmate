# Provider-neutral Daily-loop verification

For the current branch state, publication status, remaining integration steps
and calibration-cleanup correction, see
[Codex integration status](../codex-integration-status.md).

**All owner-required pre-merge reliability checks passed on 2026-11-15.**
[Current reliability verification](premerge-reliability-2026-11-15.md) covers C15
actual process startup, C16 real LaunchAgent load/deduplication, complete cold
Codex conversation reads, and normal new/resume exits for both Providers with
fresh SessionEnd and ended journals. The final combined suite passes 308/308;
131/131 selected checks pass on system Python. Calendar remains separate.

**C14 Provider integration acceptance passed on 2026-11-14.** The
[cross-Provider native report](c14-cross-provider-2026-11-14.md) completes both
Default provider variants, both real switch directions, source/history-unavailable
recovery and exact native launch/resume ownership. C14-CODEX-03 exposed a stale
shared-daemon environment; dedicated Codex launches repair it and pass fresh
native confirmation. The final suite passes 279/279, with 70/70 system-Python
compatibility checks and an independent review without findings.

Earlier Codex timestamp and Claude indexless-resume/environment corrections
remain documented below. The earlier
[cold SQLite limitation](c14-codex-sqlite-2026-11-13.md) is superseded by stable
private snapshots and actual post-exit conversation verification. Native macOS
reminder display/responses and RunAtLoad/deduplication were exercised with a
bounded alert timeout. Reboot/fresh-login and future scheduled triggers were not
performed. Calendar application import remains unverified and outside this task.
No push or merge was made.

## Final entry points and migration

Skills use the stable `deskmate` command, shared cards and the selected data root.
Morning uses `work-session`; evening discovers Provider plus native session IDs
with metadata-only `sessions` and reads individual `session-delta` results where
saved state is incomplete. Retrospective uses durable evidence, explicit selection
and bounded reads. Native spelling is `/skill` in Claude and `$skill` in Codex.
A new-session experiment keeps the recorded Provider. A missing owner/runtime
requires an explicit choice; a Provider switch requires preview and interactive
consent. Checkpoint ratings carry the current Provider.

The former Claude-only opening command and shell wrappers are removed. Existing
configuration that names the old prompt/Stop hook paths is recognized by the
Claude adapter solely to remove/replace those definitions during successful
setup. The exact old identifiers in that migration matcher and its regression
fixture are intentional; they are never invoked and are not a compatibility API.
The superseded Claude session summarizer is removed. Native measurement helpers
behind `token-usage` and the explicitly labelled Claude-only `session-stats`
diagnostic remain: they implement historical measurements, not duplicate launch,
hook or session-summary paths. Routine skill execution uses neither diagnostic.

`deskmate sessions` now defaults to all Providers and zero messages. Explicit
`--messages N --cut N` reads bounded deltas; `--cut` is the total character budget
per Work session, not a per-message clipping limit. The result reports its saved
Checkpoint boundary, coverage and omitted counts. A human listing offers a resume
command only when its Provider plus ID matches the current Project card. Other
listed sessions need a Checkpoint before normal Project routing can resume them.

## Automated and instruction scenarios

`tests/test_daily_loop.py` uses disposable homes, fake native CLIs and terminal
submission, synthetic native storage and the actual `bin/deskmate` interface.
The installation matrix covers Claude only, Codex only, both with Claude default,
and both with Codex default. It traverses setup and shared skill links, reminder
syntax, initial routing, native-hook ownership confirmation, installed prompt
hook delivery, revision-protected Checkpoint, live Checks, same-Provider resume,
retrospective candidate/selection phases, metadata-only evening discovery,
bounded missing-progress reads, fixture-authored lessons/Handoff and preserving
removal. File writing in this harness represents skill output; it does not prove
that a native model followed the skill. Both switch directions additionally run
interactive consent, native hook confirmation and one-time bundle consumption.

Before implementation, default discovery omitted Codex and disclosed Claude
conversation canaries; explicit message inspection omitted delta coverage.
These scenarios were observed failing before changing the public session facade.
Text coverage and mismatched-owner resume regressions were also observed RED
then GREEN. Codex fixtures use actual rollout message shapes, not hook events.

A separate agent applied the baseline and revised skill instructions to four
read-only synthetic scenarios: Codex-only morning and a new-session experiment;
evening with shared native IDs across Providers and missing cards; Codex
Checkpoint/rating; native study arguments with a custom data root. Baseline
application selected Claude-only launch, early conversation reads, hardcoded
personal data and a Claude-attributed Codex rating. Revised application selected
Provider-aware routing, individual deltas, the selected root and a Codex rating.
Two scenario gaps were corrected: repository discovery follows the real command
target and non-owner Handoff work retains an unresolved Provider/ID resume.
These are instruction-application observations, not authenticated runtime proof.

Commands (run from the feature source with fixture data):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -Werror::ResourceWarning -m unittest discover -s tests -q
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -Werror::ResourceWarning -m unittest tests.test_daily_loop -v
git diff --check
rg -n --hidden -g '!.git' -g '!.superpowers/**' 'tools/(sessions\.py|open_tab\.sh|log_event\.sh|hook_log\.sh|hook_tokens\.sh)|open-session' .
```

The final reference check finds the intentional legacy-hook ownership matcher
and migration fixture, the removal ledger and this search command. No live
caller dispatches a removed entry point. Historical feature plans describe
their own earlier state; current behavior is documented by README and the durable
contract. Baseline 239-test execution exposed an existing PTY harness EOF/exit
race; its affected expiry scenario passed alone, and the harness now waits for
bounded process completion instead of treating EOF as a still-running failure.
Final command results and independent review findings are recorded below after
verification, without inferring native completion.

## Native acceptance matrix — completed Provider groups

Use dedicated non-sensitive test projects and Work sessions, isolated data and
native configuration. The owner authorized the 2026-11-14 native continuation, lifting the earlier
quota hold for these tests. Personal integration state was not reinstalled.

| Scenario | Evidence required | Status |
| --- | --- | --- |
| Claude only | Setup twice, `/setup`, all five Daily-loop skills discovered, actual prompt/Stop delivery, matching Provider/session rows | Executed; see Claude evidence and repair follow-up |
| Codex only | Setup twice, `$setup`, all five skills discovered, normal `/hooks` trust, actual prompt/Stop delivery | Executed; see current Codex evidence |
| Both, each Default provider | Default-first reminders, unowned launch selects default, same shared skill/card content | Passed: repeated setup/ordering plus two real unowned launches and matching native ownership |
| Same-Provider resume | Real launched native ID and folder match the saved card; default does not override ownership | Passed: prior Claude proof plus fresh dedicated-process Codex exit/resume, native Check and exact launch-ID confirmation |
| Claude → Codex | Saved card/current Checks/bounded delta preview, explicit overlap consent, new native ID, path-only transfer, consume/delete | Passed after C14-CODEX-03 repair; conversation-only marker recovered |
| Codex → Claude | Same guarantees in reverse; no cross-Provider resume claim | Passed; post-Checkpoint marker recovered, live Check passed, new native identity confirmed |
| Source/history unavailable | Continue from card and Checks with explicit missing-context disclosure | Passed natively: unavailable Claude runtime/history, zero-message transfer, explicit unavailable coverage and successful Codex Check |
| Complete Daily loop | Actual morning → Checkpoint → selected retrospective → evening Handoff under each Provider | Both executed; original Claude run used a direct native-resume workaround |
| macOS reminders | Native display/responses, load trigger and concurrent/same-day suppression | Passed: real RunAtLoad, bounded native alert, concurrent invocation and same-day reload; no reboot or future scheduled trigger performed |
| Calendar application | Import and delivery, separately from model tests | Outside this task; remains unverified |

Record date, native versions, Provider/session identities, actual commands,
observed rows/card revisions and degraded outcomes without private conversation
content. The fixture matrix does not substitute for native evidence. The calendar and
future scheduling checks are not represented as Provider acceptance results.

## Temporary tracker disposition before merge

The durable contract is [Provider-neutral CLI](../provider-neutral-cli.md);
[ADR 0001](../adr/0001-provider-neutral-core.md) and
[development workflow](../agents/development-workflow.md) remain authoritative.
Retain `.scratch/provider-neutral-cli/` until the integration change.
Delete that entire temporary directory in the eventual integration change after
preserving the native results and checking the evidence below. It is identified
for removal, not an active post-merge documentation dependency.

| Temporary material | Durable destination before removal |
| --- | --- |
| `spec.md` | `docs/provider-neutral-cli.md` (full decisions, testing contract, deferred work) |
| C01–C02 | README command/setup/configuration sections; `tests/test_deskmate_cli.py` |
| C03 | README shared cards; `tests/test_project_cards.py`; shared-card design |
| C04–C05 | README native integration; adapter contract tests; recorded Codex usage fixture |
| C06 | README log schema; `tests/test_activity_log.py`; separate native usage contract |
| C07 | README routing/ownership; routing design; `tests/test_work_sessions.py` |
| C08 | `docs/testing/bounded-session-deltas.md` |
| C09–C10 | `docs/testing/provider-switches.md` and secret-scanner research |
| C11 | `docs/testing/progressive-retrospective.md` |
| C12 | `docs/testing/provider-reminders.md` |
| C13 | `docs/testing/installation.md` |
| C14 | This document and completed native Provider reports |
| C15–C16 and pre-merge reliability | [Current reliability verification](premerge-reliability-2026-11-15.md), focused storage and morning reports |

Ticket-level stop directives are historical execution boundaries, not changes to
the final architecture. The C12 decision to attribute desktop responses to the
displayed Default provider with no native ID remains durable in README and its
verification document. Preserve deferred findings in their existing evidence
files until resolved; acceptance is governed by the current native matrix, rather than checkbox
counts on earlier tickets.


## Independent whole-feature review and fix pass — historical

One fresh-context reviewer inspected C14 against the whole Provider-neutral
feature, including ownership/cancellation, bounded reading, consent/redaction,
cleanup, installation rollback and retrospective selection. It found two
Important issues; no new Critical or Minor findings were reported.

- Recognized YAML block credentials were counted as redacted after replacing
  only the scalar marker. Card and Session delta public regressions observed
  RED, including block/folded values, triple quotes, indented continuation,
  shell continuation and structured containers. Ambiguous recognized values now
  block preview/launch for source review, with no bundle or audit mutation.
- Abrupt termination during bundle writing left a partial final-named file that
  could never pass schema inspection for expiry. An actual crashing subprocess
  reproduced RED. Creation now writes a private reserved staging file, fsyncs
  and atomically publishes a complete bundle. Cleanup expires abandoned staging
  files after one hour using exact filename, owner, regular-file, link-count,
  permissions and inode checks; symlinks/unrelated/hardlinked files stay.
  A lock prevents deleting an active writer. Its regression failed when the lock
  was removed and passed restored; a writer's abrupt exit then permits expiry.

Review disposition: native runtime/desktop/calendar acceptance remains held;
exhaustive secret detection remains outside the heuristic redactor's guarantee;
structured Check allowlisting and non-macOS support remain documented future
work. Respectively, these leave native behavior unverified, possible unrecognized
secret formats, and the existing executable Checks/macOS-only environment. None
is silently claimed fixed or accepted by synthetic tests.


## Verified synthetic results — 2026-11-10

- Full suite on Python 3.14.6: **248/248 passed**, ResourceWarnings treated as
  errors, no skipped tests (106.897 seconds).
- Daily-loop plus transfer scenarios on macOS system Python 3.9.6:
  **27/27 passed**, ResourceWarnings treated as errors (56.710 seconds).
- Independent whole-feature review: both Important findings fixed with observed
  RED/GREEN regressions; no new Critical or Minor findings left open.
- Reference audit: no active caller uses removed entry points. The remaining
  exact old names are ownership-migration identifiers, their test and explanatory
  removal/search text. `git diff --check` passed.
- Existing feature destination verification and local checkpoint commit follow;
  native acceptance remains pending and no push/merge is authorized.

Destination full suite passed on the existing feature worktree before its local checkpoint commit. Native acceptance remains pending.


## Codex native evidence — 2026-11-11 (historical)

The Codex group ran setup/discovery/trust, actual skill and lifecycle logging,
Checkpoint/full exit/resume, selected retrospective, lessons and evening Handoff.
C14-CODEX-01 was then fixed and its fresh native regression passed without
formatting hints. See [correction evidence](c14-codex-timestamp-fix-2026-11-11.md).
At that date, C14-CODEX-02 (post-exit SQLite availability), Claude and
cross-Provider acceptance remained open. The current completed Provider matrix
and the 2026-11-14 continuation above supersede that historical status.


## Completed native continuation — 2026-11-14

See [the native report](c14-cross-provider-2026-11-14.md) and its machine-readable
evidence for the stale-daemon reproduction, RED/GREEN correction, both defaults,
both switches, degraded recovery, same-ID resume and cleanup. Historical entries
above describe their dates and do not override the completed Provider matrix.
Calendar follow-up was separated after the owner questioned its inclusion in the
Codex integration task; no calendar import or delivery result is inferred.
