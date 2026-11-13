# C14-ENV-01 Claude-only native launch environment — 2026-11-13

**Completed.** Deskmate launched and resumed the recorded Claude Work session in a
real iTerm tab with the fixture HOME, PATH, ZDOTDIR, CODEX_HOME and data. No
environment wrapper, transport adaptation or in-tab export was used.
`CLAUDE_CONFIG_DIR` stayed absent end to end. Only the Claude group was authorized.
No Codex or cross-Provider request was made. **C14 is not closed.**

- Source under test: `/private/tmp/deskmate-c14-launch-env-20261113-vh2knmgb/source`,
  base `f22022e` plus the staged launch-environment patch (under review). Not
  modified. The implementation files under `bin/ tools/ skills/ tests/ install.sh`
  were hashed before and after (53 files, identical). The staged diff of
  `tools bin skills install.sh` has sha256 `368fcbff…f65bf` both before and after.
  The pre-existing, git-ignored `tools/__pycache__` (14:57) was not touched.
- Fixture `/private/tmp/deskmate-c14-claude-20261113-dvho_hu0`: HOME `home/`,
  data `data/`, project `project/`. Claude Code `2.1.323`. Reminder channels `[]`.
- Native session `85b0fc6e-17b9-4d11-a788-c47ee19232eb`. Launch ID
  `64e50406658d4854b3a9e2ee38a67f62`. Process `86834` on `ttys005`. iTerm
  session `BBAA78EA-DE84-4AE2-8779-8C5D44162572`.
- Before the run, no fixture Claude process was alive. The only other `claude`
  processes had the personal HOME as cwd and were not part of this run.

## Steps and results

| Step | Result |
| --- | --- |
| Re-point fixture integration | **First observation:** `deskmate setup --provider claude --default-provider claude --non-interactive` from the new source exited 2: `Existing skill is not owned by Deskmate: …/home/.claude/skills/call-it-a-day; move or rename it`. **Workaround (documented flow):** ran `deskmate remove --non-interactive` from the previously selected source `…-fix-20261113-5hlu73nk` (exit 0, `personal data preserved`), then setup from the new source (exit 0, backup `363dd260…`). The skills and `~/.local/bin/deskmate` now point to the new source. All `data/` files were byte-identical before and after. |
| Caller environment | `HOME=<fixture>/home`, `DESKMATE_DATA_DIR=<fixture>/data`, `PATH=<fixture>/home/.local/bin:<fixture>/pathbin:/usr/bin:/bin:/usr/sbin:/sbin`, `CODEX_HOME=<fixture>/home/.codex`. `ZDOTDIR` and `CLAUDE_CONFIG_DIR` were **unset**. `command -v osascript` returned `/usr/bin/osascript`. `pathbin/` holds only `claude` and `python3`; there is no wrapper. |
| Dry-run | `deskmate work-session --folder …/project --dry-run` → `resume Work session with claude: …/project (ok)`, exit 0. |
| Generated command (inspection only) | Calling `provider_environment.launch_command` directly, without side effects, produced `/usr/bin/env -u CLAUDE_CONFIG_DIR -u DESKMATE_LAUNCH_ID -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT HOME=… ZDOTDIR=<fixture>/home PATH=… CODEX_HOME=… DESKMATE_DATA_DIR=… DESKMATE_LAUNCH_ID=… CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1 /bin/zsh -l -i -c 'builtin cd -- <project> && builtin exec /usr/bin/env -u … <same keys> <fixture>/home/.local/bin/claude --resume 85b0fc6e…'`. With ZDOTDIR unset, the default became the selected HOME. CLAUDE_CONFIG_DIR is explicitly unset at both levels. The CLI is an absolute path. |
| Authentication | Reused the owner-approved temporary link `home/Library/Keychains → ~/Library/Keychains`. Created 14:26:46Z, removed 14:33:40Z. No credential was read, printed or copied. |
| Real launch | `deskmate work-session --folder …/project` exit 0: `(pending)`, `Terminal command submitted; native hook confirmation is pending.` A new iTerm tab ran `<fixture>/home/.local/bin/claude --resume 85b0fc6e…` (pid 86834). The process cwd was the project folder, and the resumed conversation was visible. |
| Process environment (external) | `ps -E`, filtered to the selected keys only: HOME, PATH, CODEX_HOME and DESKMATE_DATA_DIR are the fixture values. `ZDOTDIR=<fixture>/home`. `DESKMATE_LAUNCH_ID=64e50406…`. `CLAUDE_CONFIG_DIR` is absent. |
| Hook and journal | `SessionStart` at 15:26 local with the same ID, the project cwd and `provider=claude`. New journal attempt: `mode=resume`, `requested_session_id = native_session_id = 85b0fc6e…`, `expected_revision=3`, `state=confirmed`. |
| Ownership | The card is still owned by `claude:85b0fc6e…`. The body below the front matter is byte-identical. The revision went **3 → 4**, the expected ownership-confirmation increment. |
| Native verification | One harmless request in the tab: run `deskmate check` and print only the selected keys. Manual mode raised the normal `Do you want to proceed?` prompt. **The coordinator did not approve it.** The user chose `1. Yes` in the panel, and the mode stayed manual. Raw tool result (14:32:12Z) is shown below the table. |
| Full exit | `/exit`. The `claude --resume` process (86834) is gone. `SessionEnd` was logged at 15:33 with the same ID, cwd and Provider. Journal attempt `64e50406…` has `ended=true`. |
| Exit code | **Not observed.** The command ran as the tab's own iTerm command, so the tab closed when the CLI exited and no numeric code was shown. No code is inferred. |

Raw tool result of the native verification (14:32:12Z):

```text
== C14 Claude acceptance  (active)
   probe content: ok  ok
CHECK_EXIT=0
DESKMATE=<fixture>/home/.local/bin/deskmate
PWD=<fixture>/project
CLAUDE_CODE_SESSION_ID=85b0fc6e-17b9-4d11-a788-c47ee19232eb
HOME=<fixture>/home
PATH=<fixture>/home/.local/bin:<fixture>/pathbin:/usr/bin:/bin:/usr/sbin:/sbin
ZDOTDIR=<fixture>/home
CODEX_HOME=<fixture>/home/.codex
DESKMATE_DATA_DIR=<fixture>/data
CLAUDE_CONFIG_DIR=assente
```

`<fixture>` is `/private/tmp/deskmate-c14-claude-20261113-dvho_hu0`.

## Observations and limits

- Re-pointing an installation to another checkout still needs remove + setup.
  This is the same observation as in the previous run.
- The fixture HOME has no zsh startup files. Because ZDOTDIR follows the selected
  HOME, the user's personal `~/.zshrc` was not used. Only the system `/etc/zsh*`
  files could run, and the selected keys were reapplied before `exec`. A fixture
  with its own rc files that rewrite PATH was not exercised.
- iTerm closes the tab when the CLI exits, so the CLI's numeric exit code is not
  observable on this path.
- `data/` changed only where expected: `log.csv` (start/end rows), the card
  revision, the journal, and `usage/claude.json` from the native Stop hook.
- Not executed: the new-session launch path, focusing an already-running tab,
  an explicitly set `CLAUDE_CONFIG_DIR`, desktop/calendar reminders, and any
  Codex or cross-Provider step. Codex fake tests are not native evidence.

Raw evidence: `<fixture>/evidence/launch-env/`. No source, tracker, patch,
personal configuration, push or merge was changed.

Coordinator reconciliation: the staged implementation described above was
review-approved before native execution and is committed as `31f3cc6`. The
implementation hashes in the automated evidence match the original feature
worktree; native journal end-state and auth-reference removal were also checked
independently after collecting this report.
