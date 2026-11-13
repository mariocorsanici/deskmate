# 16: Show the morning reminder when the Mac was off at reminder time

**What to build:** The morning reminder appears once per working day even when the Mac is switched off overnight and turned on after the reminder time, and never twice in the same day.

**Blocked by:** 12: Update reminders for both Providers; 13: Complete installation, migration and removal (the LaunchAgent is installed there).

**Status:** ready-for-agent

Observed: no morning reminder from 2026-11-10 to 2026-11-13 included. `last reboot` shows the Mac shut down every evening since 2026-11-09 and booted at 09:08, 09:31, 09:07 and 09:11. `com.deskmate.morning` uses `StartCalendarInterval` at 09:00: launchd runs a missed job after sleep, but not after power-off, so the run is lost. Evening reminders (17:00, Mac on) kept working. Until 2026-11-09 the Mac slept instead, and the reminder came on wake.

- [ ] `reminders.py plist morning` adds `RunAtLoad: true`, so the job also runs at login; the existing `window morning` check (09:00 −5 min / +3 h) keeps it silent outside the morning.
- [ ] The reminder is shown at most once per day: `window morning` (or the reminder script) exits without showing anything if today's reminder was already shown. The marker is written when the alert is shown, not when it is answered (the alert can stay open for an hour, and a login at 08:58 followed by the 09:00 run must not show it twice).
- [ ] Same treatment for the evening reminder only if wanted: today it is not affected.
- [ ] Install/upgrade path (ticket 13) reloads the LaunchAgent (`launchctl bootout` + `bootstrap`) so existing installations get `RunAtLoad`.
- [ ] Tests: plist contains `RunAtLoad`; window + once-per-day with a fake clock and an isolated data directory (login before the window, inside it, after it; second run on the same day).

Added on 2026-11-13 from Mario's housekeeping list (item 7b).

## Comments
