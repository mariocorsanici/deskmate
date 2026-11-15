# C14-CODEX-01 — Checkpoint timestamp correction

The timestamp finding is resolved. Publication and Session delta extraction now
share `tools/checkpoints.py`; `card write` validates a Status Checkpoint before
creating storage or replacing the card. Invalid input returns exit 2 and leaves
bytes, revision and legacy link intact. Cards without Checkpoints, existing ISO
offsets, UTC `Z` and legacy local minute timestamps retain their behavior. Invalid
older stored cards still disclose a bounded fallback.

The checkpoint skill obtains the current UTC ISO 8601 value with seconds from
Python and copies it into the candidate. No schema or CLI command was added.

## Verification — 2026-11-11

- New initial-write, update and malformed-line regressions were observed RED
  before the fix. The original CET value was accepted incorrectly.
- Card/delta suites: **47/47** on Python 3.14.6 and **47/47** on Python 3.9.6.
- Full suite: **253/253** in preparation (98.537s) and in the feature worktree
  (104.827s), with ResourceWarnings treated as errors.
- Independent review: approved; no Critical, Important or Minor findings.
- Fresh native Codex CLI 0.167.0 session
  `01a1cb36-325e-7de3-99e9-2952c94610bd`: checkpoint prompt contained no timestamp
  or format hint. The agent invoked the system clock, generated
  `2026-11-11T15:33:47+00:00` and saved revision 1 on the first attempt.
- Native retrospective first collected metadata and paused; after explicit
  selection of only that session, its delta recognized the Checkpoint with
  second precision, `coverage.origin=checkpoint`, full coverage and no warnings.
  The observed native result included 6 messages/2,064 characters, no omissions
  and no truncation, within configured 12-message/6,000-character limits.
- The native process exited 0. Temporary authentication reference removed;
  previous lessons and Handoff remained byte-for-byte unchanged.

The [regression evidence](c14-codex-timestamp-fix-2026-11-11.json) preserves the
actual prompt, system-clock invocation, native outputs, checkpoint, hook rows,
file hashes and independent public-command probes. The
[initial native run](c14-codex-native-2026-11-11.md) remains a historical record
of the failure and manually corrected test data.

## Separate post-exit SQLite observation — follow-up

A supplementary public read after CLI exit encountered `SQLITE_CANTOPEN` on the
native paginated history in read-only mode while WAL/SHM sidecars were absent.
It returned the existing explicit unavailable-history warning. This also
reproduced outside the outer sandbox. A diagnostic read-write connection doing
only SELECT recreated the sidecars, after which read-only probes succeeded on
both Python versions. This is a separate history/SQLite lifecycle limitation;
the timestamp fix does not repair it. The native Checkpoint/retrospective proof
above passed before this diagnostic. Track this separately as C14-CODEX-02
before unconditional Codex acceptance; do not describe the warmed post-exit
probe as proof that cold read-only access is reliable.

C14 remains incomplete: Claude and cross-Provider native groups are still on
hold, and C14-CODEX-02 needs triage. No push or merge was performed.

## Follow-up — 2026-11-13

C14-CODEX-02 is now triaged as a documented bounded runtime limitation; see the
[cold-WAL investigation](c14-codex-sqlite-2026-11-13.md) for reproductions inside
and outside the sandbox, public-command contracts and recovery limits. The
strict read-only production reader is unchanged. Claude-only native acceptance
was separately authorized and launched on 2026-11-13; results are pending and
the cross-Provider group remains held. C14 remains open.
