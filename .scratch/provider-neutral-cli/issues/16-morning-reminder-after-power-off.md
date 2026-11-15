# 16: Show the morning reminder when the Mac was off at reminder time

**What to build:** The morning reminder appears once per working day even when the Mac is switched off overnight and turned on after the reminder time, and never twice in the same day.

**Blocked by:** 12: Update reminders for both Providers; 13: Complete installation, migration and removal (the LaunchAgent is installed there).

**Status:** ready-for-agent

**Implementation:** completed and verified on 2026-11-15, including actual
isolated RunAtLoad, concurrent suppression and same-day bootout/bootstrap.

Observed: no morning reminder from 2026-11-10 to 2026-11-13 included. `last reboot` shows the Mac shut down every evening since 2026-11-09 and booted at 09:08, 09:31, 09:07 and 09:11. `com.deskmate.morning` uses `StartCalendarInterval` at 09:00: launchd runs a missed job after sleep, but not after power-off, so the run is lost. Evening reminders (17:00, Mac on) kept working. Until 2026-11-09 the Mac slept instead, and the reminder came on wake.

- [x] `reminders.py plist morning` adds `RunAtLoad: true`, so the job also runs at login; the existing `window morning` check (09:00 −5 min / +3 h) keeps it silent outside the morning.
- [x] The reminder is shown at most once per day: `window morning` (or the reminder script) exits without showing anything if today's reminder was already shown. The marker is written when the alert is shown, not when it is answered (the alert can stay open for an hour, and a login at 08:58 followed by the 09:00 run must not show it twice).
- [x] Same treatment for the evening reminder only if wanted: today it is not affected.
- [x] Install/upgrade path (ticket 13) reloads the LaunchAgent (`launchctl bootout` + `bootstrap`) so existing installations get `RunAtLoad`.
- [x] Tests: plist contains `RunAtLoad`; window + once-per-day with a fake clock and an isolated data directory (login before the window, inside it, after it; second run on the same day).

Added on 2026-11-13 from Mario's housekeeping list (item 7b).

## Comments

2026-11-15: implemented morning login recovery. The public morning script uses
`reminders display morning`; that command checks the configured working days and
inclusive window, serializes a per-local-date display claim under the selected
data root, and releases the lock before waiting for the native answer. Dry runs
do not create reminder state. A failure to spawn osascript removes the claim;
after spawn it is retained, including dismissal/error, because an alert may
already have appeared. Evening scheduling and snoozing retain their behavior.

Existing installation activation already reloads changed owned agents and
restores previous bytes plus active services on failure. New setup upgrade and
rollback regressions exercise that path. Focused evidence and native validation
limits: [morning verification](../../../docs/testing/premerge-morning-2026-11-15.md).
The final combined candidate passes 308 tests; 131 selected checks pass on
system Python. Independent review and actual isolated native validation passed;
see the linked report for bounded title/timeout and reboot/login limitations.
No personal LaunchAgent was changed.
