# Codex integration status

Updated 2026-11-16 for `feature/codex-cli-support`.

## Current state

C01–C16 are implemented. The agreed Provider integration and pre-merge
reliability cases have passed. No unresolved functional blocker is known within
that acceptance scope. Integration with the current `develop` is complete
locally; publication and the merge into `develop` remain.

The native acceptance covered the implementation up to `1a83dfa`; `0de0aa7`
records the subsequent correction to calibration cleanup. The `develop`
integration in `40c8a8e` changed shared logging, token usage, `check.py` and the
skills afterwards; see [Local and remote state](#local-and-remote-state).

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

Updated 2026-11-16. The status refresh `2d2713d` was pushed:
`origin/feature/codex-cli-support` pointed to it before this integration.

Integration steps completed locally:

1. `develop` (up to `74f713c`) was merged into the feature in `40c8a8e`. The
   Daily-loop follow-ups and the Agenda were ported to the Provider-neutral
   design rather than restoring the Claude-only shell hooks: `activity_log.py`
   now holds `usage_scope` and the precise `<skill>-end` markers, skills log
   through `deskmate log-event ... --provider`, and `deskmate agenda`,
   `deskmate logins` and `deskmate retro-due` replace direct tool paths.
   Per-skill token windows remain Claude-only; Codex usage stays session-wide.
2. `.scratch/provider-neutral-cli/` was removed after checking the
   [evidence mapping](testing/daily-loop.md#temporary-tracker-disposition).
3. The integrated result passed the full suite: 413/413 on Python 3.14.6 and
   413/413 on macOS Python 3.9.6, ResourceWarnings as errors, no bytecode writes.

The native acceptance above predates the integration. The integrated skills
(Agenda, goal, switches, logins, end markers) have automated coverage only;
they have not been exercised in a native Claude or Codex session.

Remaining: publish the feature commits and merge into `develop` according to
the [development workflow](agents/development-workflow.md).
