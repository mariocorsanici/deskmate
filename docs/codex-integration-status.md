# Codex integration status

Updated 2026-11-15 for `feature/codex-cli-support`.

## Current state

C01–C16 are implemented. The agreed Provider integration and pre-merge
reliability cases have passed. No unresolved functional blocker is known within
that acceptance scope. Integration into the current `develop` and publication
of the local commits remain to be performed.

The latest production change is `1a83dfa`; `0de0aa7` records the subsequent
correction to calibration cleanup. This status refresh changes documentation
only. The implementation bytes still match the actual native acceptance copy.

## Completed and verified

| Area | Current evidence |
| --- | --- |
| C01–C13: shared CLI, cards, adapters, logs, routing, bounded deltas, switches, retrospective, reminders and installation | Implemented; covered by the final automated suite and C14 native acceptance |
| C14: complete Daily loop and Provider integration | Both Default provider variants, both real switch directions, degraded recovery and exact native ownership passed |
| C15: native process startup | Private literal argv/prompt transport, bounded tty-specific process verification, new/resume and inspectable failed start passed |
| C16: morning recovery | Real RunAtLoad alert, concurrent suppression and same-day bootout/bootstrap passed in isolated data |
| Cold Codex history | Actual post-exit session and delta returned all four expected messages with full coverage and unchanged native data/file set |
| Normal session endings | Claude and Codex new/resume exited normally; each had a fresh matching SessionEnd, ended journal and absent process |
| Review | Three startup findings fixed with failing-then-passing regressions; focused final storage review had no actionable findings |

Automated results, with bytecode writes disabled and ResourceWarnings treated
as errors:

| Verification | Result |
| --- | --- |
| Complete candidate suite, Python 3.14.6 | 308/308 |
| Complete suite in the original feature worktree | 308/308 |
| Selected compatibility suite, macOS Python 3.9.6 | 131/131 |
| Exact intermediate reminder commit content | 53/53 |
| Exact intermediate Codex storage commit content | 35/35 |

See [integrated verification](testing/premerge-reliability-2026-11-15.md), its
[machine-readable evidence](testing/premerge-reliability-2026-11-15.json), and
[C14 native acceptance](testing/c14-cross-provider-2026-11-14.md).

## Calibration cleanup correction

The owner reported two terminals showing `DESKMATE_FAKE_INPUT_READY`. These
were earlier disposable input-calibration programs still waiting for input.
The first cleanup checked real Provider processes and missed these separate
programs. Both fake programs and their runners subsequently exited through
normal input, and their tabs closed; other work terminals were preserved.
A final audit of the exact calibration executable path found no remaining
processes. The original native Provider acceptance was separate and remains
valid. The detailed report and JSON explicitly retain this correction.

## Verified limits and checks not performed

- Morning recovery was tested through actual LaunchAgent load in the existing
  GUI login, with fixture day/time and a five-second native alert. A complete
  reboot, fresh login, future scheduled trigger and personal-agent installation
  were not exercised. Existing-installation reload/rollback has automated coverage.
- Cold snapshots require stable native files and directory metadata. Incomplete
  sidecars, unknown schemas, corruption and writer races report degradation.
  Live WAL uses ordinary SQLite coordination; an unchanged live sidecar set
  across external writer transitions is not guaranteed. See
  [storage boundaries](testing/premerge-cold-history-2026-11-15.md).
- Calendar application import/delivery remains outside this effort and
  unverified. Future platform support, analytics, structured Checks and optional
  external secret scanning remain in the [roadmap](../ROADMAP.md).

## Local and remote state

The remote branch was checked with `git ls-remote` during this refresh:
`origin/feature/codex-cli-support` points to
`c23d6938b9006e1bd58fbb5cb3cc8368a83647aa`. The completed work and this status
update are local commits; this task has performed no push or merge.

Before merging:

1. Remove `.scratch/provider-neutral-cli/` in the integration change, after
   checking the durable evidence mapping in
   [Daily-loop verification](testing/daily-loop.md#temporary-tracker-disposition-before-merge).
2. Reconcile the feature with the current `develop`; both contain independent
   commits. Resolve any conflicts and run the suite on the integrated result.
3. Publish the reviewed feature commits and perform integration according to
   the [development workflow](agents/development-workflow.md).
