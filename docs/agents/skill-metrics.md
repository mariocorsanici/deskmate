# Skill usage boundaries

Read this at the start of each Deskmate skill and follow the completion step
before sending its final reply. The measurement is the work up to an explicit
marker; it does not include any final model reply generated after that marker.

## Capture this invocation

Identify the Provider (`claude` or `codex`) and this native Work session from
runtime-provided identity or its current transcript's native metadata. Read
`<data>/log.csv` from the Deskmate data root (`DESKMATE_DATA_DIR`, otherwise
`<repo>/data`). Capture the matching start row for this skill, this Provider,
this native session ID and its starting folder before doing the skill's work;
keep that identity for the completion step. The native hook writes the start
event. For repeated invocations, use the current unmatched start occurrence in
that session, not an older occurrence.

A globally latest row, or a matching folder alone, cannot identify a native
session when several sessions are running. If native identity or the matching
start is unavailable/ambiguous, continue the skill without an end event and say
that its usage remains a legacy window. Do not borrow another session's identity
or ask for credentials to obtain it.

## Complete the measurement

After the skill's required work is done and the final reply is ready, run its
end command with the captured Provider, native session ID and starting folder as
the final tool action, then send the prepared reply:

```bash
deskmate log-event <skill>-end "" "<session-id>" "<starting-folder>" --provider <claude|codex>
```

The logger fills an empty detail with a precise UTC timestamp. Keep that field
empty; an invented timestamp would make the measurement unreliable. Quote the
arguments as shell literals.

Interactive skills remain open while waiting for the user's choices. An early
return, cancellation, failed required write, or an unfinished skill does not get
an end event. If completion logging fails, report the measurement as unavailable;
do not claim a bounded cost. The Stop hook recomputes matching usage after the
turn. Transcript parsing retains the earliest end marker or next command, with
session end as the historical fallback.

`usage_scope=end-marked` identifies a Claude run actually bounded by a valid
matching marker. `legacy-window` includes historical or incomplete Claude runs
measured until the next command/session end. Per-skill token windows are
computed from Claude transcripts only: Codex skill rows keep an empty
`usage_scope` and their end events record completion time, while Codex usage
stays session-wide in `deskmate metrics`. End-event rows contain metadata, never
usage totals. Retrospectives compare skill costs only across `end-marked` rows;
session-wide experiments may still use their separately named session metrics.
