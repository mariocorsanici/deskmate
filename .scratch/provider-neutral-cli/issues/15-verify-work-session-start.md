# 15: Verify that a launched Work session actually started

**What to build:** After opening a Work session in a new iTerm tab, Deskmate confirms that the Provider process is running in that tab, and reports an error instead of success when it is not. Long prompts must not travel through the terminal line.

**Blocked by:** 07: Route Work session launch and resume.

**Status:** ready-for-agent

**Implementation:** completed on 2026-11-15. Both adapters share private argv
transport and bounded tty-specific native process verification. Native new and
resume acceptance passed for both Providers; see
[pre-merge verification](../../../docs/testing/premerge-reliability-2026-11-15.md).

Originally observed on `develop` (`tools/open_tab.sh`, before this branch): a long `--new` prompt was cut by iTerm's `write text` with no error, Claude never started, and the script still exited 0. Before this repair the adapters likewise returned after terminal submission without checking the native process.

- [x] The prompt uses a private payload (file 0600, directory 0700), read and deleted before native Popen. The short terminal command names only the private payload path; argv is delivered literally without shell interpolation for both adapters.
- [x] AppleScript returns tty and native iTerm session UUID; `launch()` waits up to about 10 seconds for the selected Provider process on that tty.
- [x] Missing native process returns `status: error` with tty/tab diagnostics; an early failed start remains inspectable and Work session error rendering includes those details.
- [x] Resume receives the same process check.
- [x] Regressions cover long quoted/multiline prompts, missing/wrong Provider, bounded diagnostics and cleanup without real tabs. Separate actual iTerm calibration and native new/resume acceptance passed.

Added on 2026-11-13 from Mario's housekeeping list (item 7a); not implemented on `develop` because this branch deletes `open_tab.sh`.

## Comments

2026-11-15: independent review found interpreter-shim resolution, TERM cleanup
and interruption payload cleanup gaps. Each reproduced RED, then passed after
repair. Real iTerm calibration additionally corrected the dictionary's coercion
of bare `tab`; the returned delimiter now uses ASCII character 9. Startup proves
process liveness only: hooks alone confirm native IDs and Project ownership.
