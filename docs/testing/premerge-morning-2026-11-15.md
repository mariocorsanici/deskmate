# Morning recovery verification — 2026-11-15

C16 adds `RunAtLoad` only to the morning agent. The morning script delegates to
`reminders display morning`, which checks configured working days and the
inclusive configured time minus five minutes / plus three hours. Its lock covers
only the display decision and spawn. A private per-local-date claim lives under
`<data>/.reminders/`; it precedes waiting for the answer, so login and scheduled
invocations cannot duplicate an unanswered alert. The original configured
Provider is retained for response logging even if preferences change meanwhile.

Dry runs return before creating state. Calls outside the day/window also leave
no claim. A failure to spawn osascript removes the claim. Once the native process
has started, the claim stays even if the process reports an error: the alert may
have appeared or been dismissed. This is an at-most-once native display attempt;
there is no transactional acknowledgement API proving pixels reached the screen.
The initial deterministic pass did not exercise a native alert; the isolated
native acceptance below does. Evening behavior remains covered by its existing
snooze, ignored-response and Provider tests.

The clock is fixed inside a test-only Python launcher at the reminder process
boundary. Tests execute the real shell scripts and reminder implementation,
replacing only the clock and native osascript executable. Rendering, calendar and
plist scenarios retain the public CLI dispatcher. Six concurrent script starts
share an isolated data directory; five must finish while the single alert double
is still waiting for an answer, and a seventh scheduled invocation stays silent.

Installation scenarios call real `deskmate setup` with disposable homes and a
stateful launchctl replacement. They upgrade a previously active agent without
RunAtLoad, verify bootout/bootstrap reload, and force bootstrap failure to verify
restoration of the prior active service and exact plist bytes. Existing
transactional installation code required no changes.

RED evidence: initial reminder/installation run: 53 tests, 9 failures (8 expected
feature assertions plus a test launcher csv.Error handling defect). After fixing
the launcher, reminders alone: 18 tests, 6 expected failures in 5 test methods;
the working-day test reports two subcases. Both installation upgrade tests also
failed on the missing login behavior in the initial run. The first GREEN run
found one test readiness race, corrected by waiting for both native readiness and
completion of the duplicate callers; production code did not change for it.

Focused verification:

```sh
python3 -B -Werror::ResourceWarning -m unittest tests.test_reminders tests.test_installation -q
# Python 3.14.6: 53 tests, OK

/usr/bin/python3 -B -Werror::ResourceWarning -m unittest tests.test_reminders tests.test_installation -q
# Python 3.9.6: 53 tests, OK
```

External task evidence retains both logs. Root owns combined full-suite
verification at a stable integration boundary, final
independent review and the remaining pre-merge integration gate. No personal
installation, personal LaunchAgent change, calendar operation or native model
request was performed.

## Isolated native acceptance

On macOS 26.6.2, 2026-11-15 at 17:50 local time, the standalone
`native_morning.py` harness passed against the source files in place. It created
a private temporary HOME and data root, configured today as a working day and the
current minute as morning time, and generated the plist with the real public
`reminders plist morning` command. The generated `RunAtLoad` and actual source
`morning_reminder.sh` ProgramArguments were preserved. A unique label,
`com.deskmate.premerge.nativec16wsnhg2zi.morning`, was bootstrapped directly from
the fixture; nothing was installed under the personal LaunchAgents directory.

The fixture osascript wrapper accepted only the expected morning alert. It
changed its title to `Deskmate C16 isolated validation`, reduced its giving-up
timeout to five seconds, and delegated to the real `/usr/bin/osascript`. The
native process exited successfully after 5.19 seconds with the natural timeout;
the real reminder logged one `ignored` response for Codex. Three concurrent
direct invocations of the actual source script all exited successfully in a
combined 0.192 seconds while the native process was still open, with exactly one
native display attempt. A real `launchctl bootout` followed by `bootstrap` ran
the same job again on the same local date, exited successfully, and left both the
native attempt count and response log at one.

The `finally` cleanup booted out only the unique fixture label; a subsequent
`launchctl print` returned 113 (service absent). Source hashes before and after
matched for `tools/reminders.py`, `tools/morning_reminder.sh` and `bin/deskmate`.
Complete command, launchd state, native-process and cleanup evidence is retained
under the external run directory in `native-c16-wsnhg2zi/result.json`, with a
copy in `evidence/c16-native.json` and summary in `evidence/c16-native.log`.

An earlier native run was acknowledged before the timeout. It already proved
RunAtLoad and concurrent suppression, but an overly strict harness duration
assertion prevented its reload step. Its unique service was also removed. That
incomplete evidence remains in `native-c16-5dnlg_va/result.json`; production code
was unchanged while correcting the harness and rerunning the complete flow.

This acceptance proves a real RunAtLoad job and real native alert under the
current GUI login. It does not simulate a reboot or a fresh login, wait for a
future scheduled calendar trigger, or exercise personal installation. The
configured day/time is fixture-specific; arbitrary days and window boundaries
are covered by the deterministic suite. Alert title and duration were bounded
for this validation, and native display success still does not provide a
transactional acknowledgement of physical screen pixels.
