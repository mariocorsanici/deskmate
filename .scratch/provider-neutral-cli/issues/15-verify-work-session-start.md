# 15: Verify that a launched Work session actually started

**What to build:** After opening a Work session in a new iTerm tab, Deskmate confirms that the Provider process is running in that tab, and reports an error instead of success when it is not. Long prompts must not travel through the terminal line.

**Blocked by:** 07: Route Work session launch and resume.

**Status:** ready-for-agent

Observed on `develop` (`tools/open_tab.sh`, before this branch): a long `--new` prompt was cut by iTerm's `write text` with no error, Claude never started, and the script still exited 0. On this branch the same path is `tools/adapter_claude.py` `launch()`: it builds one command line with the prompt inside (`shlex.join([*context, *argv])`), sends it with `write text`, and returns `status: ok` as soon as `osascript` returns, without checking the tab.

- [ ] The prompt does not go through the terminal line: it is written to a private temporary file (mode 0600, removed after start) and the command reads it (e.g. `claude -- "$(cat <file>)"`), so the line stays short whatever the prompt length. The same applies to the Codex adapter if it launches the same way.
- [ ] The AppleScript returns the new session's `tty`; `launch()` waits up to a bounded time (about 10 s) for a Provider process (`claude` / `codex`) on that tty.
- [ ] If none appears, the result is `status: error` with a clear warning (tab left open for inspection) and the caller (`/whats-on-today`) tells the user which tab did not start.
- [ ] Resume (`--resume <id>`) gets the same check.
- [ ] Tests: a prompt over 1,000 characters, a prompt with quotes and newlines, and a launch whose process never appears (fake `ps`), all without opening real tabs.

Added on 2026-11-13 from Mario's housekeeping list (item 7a); not implemented on `develop` because this branch deletes `open_tab.sh`.

## Comments
