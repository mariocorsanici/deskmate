# C14-CLAUDE-01 — indexless native resume

The repair uses native SessionStart metadata already recorded in Deskmate's
activity log when Claude provides no sessions index. It requires an unambiguous
canonical folder and exactly one existing native transcript. Existing index
metadata remains authoritative; filenames and folder keys alone do not permit
resume. Discovery and routing never open conversation transcripts.

The original Claude Code 2.1.323 fixture contains a valid native transcript and
matching lifecycle hooks but no `sessions-index.json`. Its public resume dry-run
returned exit 4, `session_unavailable`, even though real native `claude --resume`
had succeeded. The repaired public command now returns exit 0 on that same
fixture, with the correct Provider, session and folder. Metadata-only discovery
also identifies its canonical folder. Data-file hashes are unchanged.

## Regression scope

Two initial public regressions failed before implementation: resumability and
metadata-only discovery of an indexless session with native lifecycle evidence.
A third RED/GREEN check protects recent file activity after an older native
start. Additional contracts reject missing files, multiple native file matches,
conflicting folders, other-Provider identity and broken logs; an existing native
index cannot be overridden by lifecycle fallback. No transcript content is
needed, and invalid-UTF8 transcript fixtures still route correctly.

Fallback activity combines hook times with file modification time, which is an
approximate freshness signal. Native indexes retain their existing period rules.
Sessions without a recorded native start and unique native file remain explicitly
degraded or refused. No new persistent store, migration or model request is used.

## Verification and limits

Final preparation suite: **263/263 passed** in 107.043 seconds, Python 3.14.6.
System-Python 3.9.6 adapter/routing/delta checks: **76/76 passed** in 65.110
seconds. Both treat ResourceWarnings as errors and disable bytecode writes.
Independent review approved with no Critical, Important or Minor findings; its
separate system-Python adapter (17) and routing (32) suites passed.
The [JSON evidence](c14-claude-resume-fix-2026-11-13.json) records commands and
outputs; original-worktree application and destination verification follow.
The original authenticated run is preserved in the
[Claude native report](c14-claude-native-2026-11-13.md).

This repairs public eligibility and discovery. Actual terminal submission with
the repaired source was not exercised in this step; direct native resume was
verified in the original run. Manual trust/permission dialogs, desktop/calendar
and cross-Provider native scenarios remain separate unfinished acceptance.
C14 remains open; no push or merge is performed.

Destination verification: **263/263 passed** in 109.403 seconds in the original feature worktree, ResourceWarnings as errors.

## Authenticated native follow-up

The [real resume follow-up](c14-claude-native-resume-2026-11-13.md) now verifies
Deskmate submitting a real iTerm launch and resuming the same Claude native
identity/folder. A SessionStart confirmed the launch journal; the unchanged
owner/body received revision 3 (from 2) through ownership confirmation. The
read-only Check passed; full exit returned 0 and SessionEnd marked the confirmed
attempt ended. Manual-mode approval was observed; the approver is inferred, not
directly identified. The temporary auth link was removed.

The fixture used an explicitly documented osascript transport wrapper to pass
its isolated HOME/PATH into iTerm. Production propagation of a custom HOME was
not tested or added. No source changes were made during native verification.
Implementation commit: `ecf9109`; Codex evidence commit: `3fe01e7`. Cross-Provider
requests remain held and C14 stays open.
