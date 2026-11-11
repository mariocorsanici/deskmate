# C14 Codex native execution — 2026-11-11

Historical execution completed with one open finding, **C14-CODEX-01**.
The [subsequent correction and native rerun](c14-codex-timestamp-fix-2026-11-11.md)
resolved that timestamp finding; a separate post-exit SQLite observation remains
for triage. The original observed results below are preserved. The complete native
loop ran on Codex CLI `0.167.0`, using source commit
`24b431f132d1a04ab5bd64ee6d3f211ed57be8b3`. C14 remains open.

The owner authorized completing the Codex group. The previous temporary project
was unavailable, so this run used a fresh isolated home, Codex configuration,
data directory and non-sensitive project under
`/private/tmp/deskmate-c14-codex-20261111-57yyvc_9`.
The native session ID was `01a1c9ea-5895-7262-ab1c-e7a3ebe266d6`.

## Observed results

| Scenario | Result |
| --- | --- |
| Setup twice | Preflight and native `$setup` exited 0; only Codex selected, preferences preserved, repeated setup required no new backup. |
| Native skill discovery | All five Daily-loop skills and setup appeared in the native `/skills` picker with their descriptions. Explicit-only skills need not appear in the model's implicit catalog. |
| Hook trust | Native startup requested review of four definitions. Reviewed SessionStart, trusted it, then trusted the remaining hooks through the native UI. All four trust hashes persisted; no trust bypass used. No separate project-trust prompt appeared with workspace-write and on-request approvals. |
| Native hook delivery | The isolated CSV contains all five skill events, two session starts and two session ends, with the same Codex identity and project path. Native Stop processing produced and updated the separate Codex usage snapshot. |
| Morning | `$whats-on-today` reconstructed first-day state, disclosed absent cards/Handoff and verified the probe file. |
| Checkpoint and resume | Initial card revision 1 saved with a passing read-only Check. Deskmate's dry-run route selected Codex resume and the recorded ID. Fully exited the CLI, resumed that ID, verified runtime identity/folder/Check and saved revision 2. Both native processes exited 0. |
| Study later | `$study-later` added one topic to the isolated list. |
| Selected retrospective | Native collection showed the complete candidate list and paused without reading messages. After explicit operator selection, read only the chosen bounded delta. Exposed the timestamp finding below; repeated successfully after correcting the test card through a new native Checkpoint. |
| Lessons | After operator feedback, appended the Italian retrospective, evidence limits and two agreed experiments to `lessons.md`. |
| Evening | `$call-it-a-day` ran the live Check, discovered metadata without messages, excluded extra reads of the current session and wrote an Italian Handoff for 2026-11-12, retaining Provider, native ID, folder and the open finding. No previous Handoff existed to archive. |

## Open finding: C14-CODEX-01

The native checkpoint skill wrote `2026-11-11 15:09 CET` into the card. The
Session delta reader rejected this timestamp and returned:

```text
Saved Checkpoint is unreadable or invalid; coverage starts at session start.
```

The card was readable and its Provider/session identity matched. A public
`deskmate session-delta --provider codex --session-id <id> --format json` probe
reproduced `checkpoint: null`, with coverage starting at session start. An
in-memory diagnostic changing only the timestamp to an ISO value with a numeric
offset made the real saved-checkpoint reader accept it.

The first selected delta respected the configured 12-message/6,000-character
limits and disclosed partial coverage and truncation: 12 messages/3,877
characters included; 12 messages/3,949 characters omitted. The fallback was
visible, but the latest saved Checkpoint did not bound the read as intended.

Asked the native `$checkpoint` skill to write a new revision using ISO 8601 with
a numeric offset. Revision 3 used `2026-11-11T15:23:20+01:00`. The repeated native
retrospective recognized the card boundary with second precision and no warning.
An independent public-command rerun also returned `coverage.origin=checkpoint`,
full coverage and no warnings.

This corrects the **test data**, not the implementation. The native writing flow
still needs to reliably produce or validate a timestamp accepted by its reader;
the successful rerun does not establish that this finding is fixed.

## Evidence and scope

The [machine-readable evidence](c14-codex-native-2026-11-11.json) preserves all 11
completed native answers, actual hook rows, native retrospective command calls,
card revisions, initial candidates, deltas before/after the correction, lessons,
Handoff, trust hashes and usage snapshots. All 92 archived source files matched
the original commit after the run. The temporary authentication symlink was
removed after both native processes exited.

Claude and cross-Provider groups remain unexecuted and on hold. Desktop/calendar
delivery was not exercised. Resume used the real native CLI after checking the
Deskmate route; iTerm launch submission was not tested. No personal integration
was installed, no implementation was changed, and no push or merge was performed.

Codex execution is complete with the finding recorded; it is not an unconditional
acceptance pass. C14 and integration into `develop` remain open.
