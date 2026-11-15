# Integration reliability verification — 2026-11-15

The owner required C15, C16, cold Codex history and proven normal session endings
before merging `feature/codex-cli-support`. All four now have implementation or
diagnosis evidence plus actual macOS acceptance. This extends the
[completed C14 Provider acceptance](c14-cross-provider-2026-11-14.md).
Calendar application work remains outside this task. No push or merge was made.

## C15: verified process startup

Both adapters use `tools/terminal_launch.py`. A private argv payload (0700
directory, 0600 file) keeps long prompts out of terminal input and AppleScript
arguments. The runner validates and removes it before native Popen. iTerm
returns tty plus native terminal UUID; a bounded ten-second poll verifies the
selected executable on that tty. Native hooks separately establish session ID
and Project ownership. Missing/wrong processes return actionable diagnostics;
an early failed start stays available for inspection. Resume uses the same path.

Eleven transport tests cover literal long quoted/multiline prompts, startup and
resume, wrong/missing process, bounded diagnostics, dry run, interpreter shims,
interrupt cleanup and real PTY termination/reaping. Independent review found
three Important gaps: resolved interpreter paths, TERM waiting for inspection
input, and KeyboardInterrupt payload cleanup. Each failed a regression before
repair and passed afterward. No findings remain from that review.

Real iTerm calibration delivered a literal 2450-character prompt with quotes,
newlines and shell metacharacters without executing them. The native terminal
received exact control bytes `1504032f717569740d`. An intentionally invalid
executable image returned failure with tty/tab diagnostics after the bounded
wait; its inspection tab remained open. Calibration exposed iTerm's coercion of
bare `tab` to the literal string; the delimiter now uses ASCII character 9.

## Normal native new/resume lifecycle

The trusted isolated C14 fixture was reused, with all 39 implementation files
updated and SHA256-checked against the candidate. Claude Code 2.1.325 and Codex
CLI 0.168.0 ran through the public Work session command in actual iTerm tabs.
Both new and same-ID resumed sessions answered an innocuous marker request;
the resume request omitted the marker and required its recovery from context.

| Provider | Native session ID | New and resume result |
| --- | --- | --- |
| Claude | `4a3e277a-5b13-42ce-ae39-49c39e22562f` | Actual PID/tty start, correct answer, normal `/exit`, fresh matching SessionEnd, exact journal ended, PID absent |
| Codex | `01a1ded4-d8a3-7bd0-acd3-bcb8851fce6c` | Actual PID/tty start, correct answer, normal `/quit`, fresh matching SessionEnd, exact journal ended, PID absent |

Every closure required a new CSV event after its saved pre-exit row boundary,
so an earlier SessionEnd for the same resumed ID could not satisfy the proof.
No forced termination, fabricated event or journal rewrite was used. All four
returned native PIDs and fixture-specific process arguments were absent at
cleanup; both temporary authentication references were removed without reading
credential values. Personal integrations and normal native trust were preserved.

The old failed closing attempt had duplicated `/exitexit` input. Fresh testing
also exposed two harness assumptions: Codex creates an idle thread only after
the first prompt, and iTerm screen reads can lag staged input. The harness now
waits for real native ownership after the harmless first message and checks the
complete exit command before pressing Enter once. No additional native closing
defect reproduced, so no synthetic lifecycle finalizer was added.

## Cold Codex conversation after exit

After normal Codex resume exit, the actual `thread_history_1.sqlite` had no
WAL/SHM. Public `session` returned status `ok` with all four expected user and
assistant messages; `session-delta` returned status `ok`, full coverage, zero
omissions and both marker answers. Native main/WAL SHA256 and the complete
metadata/history filename set were unchanged across both reads. Metadata retained
its legitimate live WAL/SHM pair; SHM coordination bytes are excluded from hashes.

An earlier acceptance read exposed an installed SQLite variant that created
empty history WAL/SHM despite `mode=ro`. That failed check is retained. The final
helper sends known sidecar-free sources directly to a stable private snapshot;
it never opens those native cold files with SQLite. A regression for the
sidecar-creating variant failed before this correction and passed after it.
Only private snapshots are immutable. Complete live WAL+SHM pairs use normal
read-only coordination; incomplete sidecars or races degrade explicitly.
[Storage verification](premerge-cold-history-2026-11-15.md) records cleanup,
writer-race tests, limits and the focused independent review without findings.

## C16: real RunAtLoad and once-per-day behavior

Morning agents now include RunAtLoad. The display command checks working days
and the inclusive -5-minute/+3-hour window, then claims the local date before
waiting for an answer. Concurrent triggers share a lock. Existing installation
reload/rollback behavior is covered by upgrade and forced-failure regressions.

A uniquely named disposable LaunchAgent bootstrapped the actual morning script
and displayed one real native alert. Three concurrent calls finished silently
while that alert was open. Real bootout/bootstrap on the same date ran the job
again without another alert or log row. The alert timed out after 5.19 seconds;
only test title and timeout were bounded. The unique agent was removed and both
native alert PIDs were absent. No reboot, fresh login, future scheduled trigger
or personal-agent installation was exercised; actual RunAtLoad plus deterministic
day/window tests establish the recovery mechanism. See
[morning verification](premerge-morning-2026-11-15.md).

## Verification and retained evidence

The final combined suite passed **308/308** on Python 3.14.6 (194.908 seconds).
The selected transport/storage/adapter/routing/reminder/installation suite passed
**131/131** on macOS Python 3.9.6 (175.710 seconds).
Final automated results and compact native evidence are in the accompanying
[JSON record](premerge-reliability-2026-11-15.json). Tests disable bytecode writes
and treat ResourceWarnings as errors. The original feature worktree also passed
the full **308/308** suite in 190.456 seconds before local checkpoint commits;
its implementation hashes match the native acceptance copy.
Exact index exports for the focused reminder and storage commits additionally
passed their complete relevant suites, 53/53 and 35/35 respectively, before
those local commits were recorded.

External raw logs, historical failed assertions, scoped native drivers and full
screen/launchd state remain in
`/private/tmp/deskmate-premerge-20261114-wfo47gku`. The durable JSON retains only
non-sensitive test content, selected native facts, hashes and cleanup results.
Historical C14 reports describe their own dates; this report supersedes their
cold-history and launchd limitations for the implemented mechanisms above.
