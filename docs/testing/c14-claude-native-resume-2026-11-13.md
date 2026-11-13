# C14 Claude native resume through Deskmate — 2026-11-13

Follow-up to the [Claude-only run](c14-claude-native-2026-11-13.md) after the
C14-CLAUDE-01 correction. **Completed: Deskmate launched and resumed the recorded
Claude Work session in a real iTerm tab.** Only the Claude group was authorized.
No Codex or cross-Provider request was made. C14 is not closed.

- Corrected source under test: `/private/tmp/deskmate-c14-claude-fix-20261113-5hlu73nk/source`,
  base `3fe01e7`, uncommitted staged fix (11 files; staged-diff sha256
  `9f3dce10…7b0`, identical before and after the run). Not modified.
- Claude Code `2.1.323` in the existing isolated fixture
  `/private/tmp/deskmate-c14-claude-20261113-dvho_hu0` (HOME, config, data,
  project). Reminder channels stayed `[]`.
- Native session: `85b0fc6e-17b9-4d11-a788-c47ee19232eb`. Launch ID
  `7a0b081e2e6946ca8a9c6708edbdfa7f`. Process `62903` on `ttys004`.

## Steps and results

| Step | Result |
| --- | --- |
| Update fixture integration | **First observation:** `deskmate setup --provider claude --default-provider claude --non-interactive` from the corrected source exited 2: `Existing skill is not owned by Deskmate: …/skills/call-it-a-day; move or rename it`. The existing links pointed to the other checkout's `skills/`; nothing was published. **Workaround (documented flow):** `deskmate remove --non-interactive` from the original source (exit 0, data preserved), then setup from the corrected source (exit 0, backup `22138eea…`). Skills, hooks and `~/.local/bin/deskmate` now point to the corrected source. `config.json` and the card were byte-identical. |
| Route | `deskmate work-session --folder …/project --dry-run` → `resume Work session with claude: …/project (ok)`. |
| Launch inspection | The Claude adapter writes `cd <folder> && … /usr/bin/env DESKMATE_LAUNCH_ID=… DESKMATE_DATA_DIR=… claude --resume <id>` into a **new iTerm tab with the default profile**. That profile's shell has the personal HOME/PATH, and the command does not set HOME. Launching unmodified would have run the personal Claude configuration, so it was not done. |
| Test adaptation | A transport wrapper named `osascript`, placed only in the fixture PATH (`pathbin/`), prefixed the submitted command with `export HOME=<fixture>/home PATH=<fixture PATH> DESKMATE_DATA_DIR=<fixture>/data; unset CLAUDE_CONFIG_DIR CODEX_HOME CLAUDECODE CLAUDE_CODE_ENTRYPOINT;` and appended an exit-code echo. It passed the focus-check call through unchanged. This is a **test transport, not a product feature**. The original and transported commands are logged; the wrapper is kept as evidence and removed from PATH. |
| Authentication | Reused the owner-approved temporary link `home/Library/Keychains → ~/Library/Keychains` (created 12:55:47Z, removed 12:58:24Z). No credential was read, copied or printed. |
| Real launch | `deskmate work-session --folder …/project` exit 0: `(pending)`, `Terminal command submitted; native hook confirmation is pending.` A new iTerm tab ran `claude --resume 85b0fc6e…`, with process cwd = the project folder. The resumed conversation was visible. |
| Hook and journal | `SessionStart` at 13:56 local with the same ID, cwd and `provider=claude`. `work-sessions.json`: one attempt, `mode=resume`, `requested_session_id = native_session_id = 85b0fc6e…`, `expected_revision=2`, `state=confirmed`. After exit: `ended=true`. |
| Ownership | Card still owned by `claude:85b0fc6e…`; body unchanged. Revision **2 → 3** at 13:56:02, written by the ownership confirmation (`claim_ownership_locked` always writes `revision+1`, even for the same owner). |
| Confirming request | Asked in Italian to run `deskmate check` and report ID/folder. Native result: `probe content: ok`, `EXIT=0`, `SID=85b0fc6e…` (`CLAUDE_CODE_SESSION_ID`), `pwd` = project folder. |
| Full exit | `/exit` → `claude exited rc=0`. No remaining resume process. `SessionEnd` at 13:57 with the same ID/cwd/Provider. |

## Approvals (manual mode)

The session started in `auto`. Shift+Tab, a normal UI action, cycled through
accept-edits and plan to `⏸ manual mode on`. The organization does not force
`auto`. In manual mode the Bash call raised the normal prompt:

```text
Bash command … deskmate check; echo "EXIT=$?"; echo "SID=$CLAUDE_CODE_SESSION_ID"; pwd
A variable in this command can't be checked before it runs
Do you want to proceed?
❯ 1. Yes   2. Yes, and switch to auto mode   3. No
```

The coordinator's attempt to press Enter was **blocked by its own permission
classifier** and was not delivered. The command ran about 18 s after the request,
so it was approved in the visible panel by a human. The mode stayed manual, so
option 1 was chosen. A later coordinator Esc reached an already-empty prompt
with no effect. Manual approval prompts are therefore observed; the approving
person is inferred from timing and the blocked keystroke.

## Limits and observations

- The launch depends on the iTerm default profile's environment. Without the
  test transport, a Deskmate launch from an isolated `DESKMATE_DATA_DIR`
  would run Claude with the personal HOME/configuration. Only `DESKMATE_DATA_DIR`
  and `CODEX_HOME` are forwarded. This matters for isolated fixtures and custom
  homes; it was not exercised with the personal HOME.
- Re-pointing an installation to a different checkout needs remove + setup.
  Setup treats links into another checkout's `skills/` as unowned.
- A same-owner resume bumps the card revision without content change. This is
  by design in the code; recorded so it is not mistaken for a Checkpoint.
- The transported shell is the user's interactive zsh. Its rc files ran before
  the exported variables, so only unset/overridden variables are controlled.
- Not executed: desktop/calendar reminders, the new-session launch path,
  focusing an already-running tab, any Codex or cross-Provider step.
- The iTerm tab used for the launch remains open with the fixture variables
  exported in its shell.

No source, tracker, patch, personal configuration, push or merge was changed.

## Selected environment correction

The wrapper limitation above is addressed by implementation `31f3cc6`; see the
[environment correction](c14-launch-environment-2026-11-13.md) and the subsequent
[real native run without a wrapper](c14-launch-environment-native-2026-11-13.md).
Earlier run observations remain historical evidence. C14 remains open.
