# C14 Claude-only native execution — 2026-11-13

Completed with one open finding, **C14-CLAUDE-01**. The run used source commit
`8ab2f78a817a9919428d75d56496f31adaf90fa4` (isolated copy of
`feature/codex-cli-support`) and Claude Code `2.1.323`. The cross-Provider group
stays suspended and C14-CODEX-02 stays open. **C14 is not complete.**

The owner authorized native Claude requests for this group. Isolated workspace:
`/private/tmp/deskmate-c14-claude-20261113-dvho_hu0`, with dedicated `home/`
(HOME and Claude configuration), `data/` (`DESKMATE_DATA_DIR`), a non-sensitive
`project/` containing `manual-probe.txt`, and a PATH that exposed only `claude`
and `python3` (Codex unreachable). Reminder `channels` were `[]`, so no
LaunchAgent or calendar file was produced. The native session ran in a visible
iTerm split, driven via iTerm AppleScript (type text, Enter, read screen).

Native session used for the Daily loop: `85b0fc6e-17b9-4d11-a788-c47ee19232eb`
(new process exit 0, resume process exit 0).

## Observed results

| Scenario | Kind | Result |
| --- | --- | --- |
| Setup twice | command | `deskmate setup --provider claude --default-provider claude --non-interactive` exited 0 twice. First run linked six skills, merged five hook groups into `settings.json`, created backup `f8ee66d7…`. Second run: no `Updated` lines, byte-identical home/data snapshot, `config.json` identical to pre-setup preferences, no new backup. **Passed.** |
| Native `/setup` | native | Ran `./install.sh --provider claude --default-provider claude --non-interactive`, exit 0, preferences unchanged, synthetic verification reported as synthetic, native verification left to `/checkpoint`. **Passed.** `setup` is intentionally not a logged skill (`tools/hook_event.py` `SKILLS`). |
| Skill discovery | native | Typing each name in the native `/` picker showed `whats-on-today`, `study-later`, `checkpoint`, `how-did-it-go`, `call-it-a-day` and `setup` with their descriptions and source `(user)`. The first `/whats-on-today` capture was too early and was repeated. **Passed.** |
| Hook logging | native | Isolated `log.csv` has session-start/end for every process and one row for each of the five skills, all `provider=claude`, the project `cwd` and the native ID, with turns/tokens on skill rows. The async `Stop` hook wrote `data/usage/claude.json` for the same ID. **Passed.** |
| Morning | native | `/whats-on-today` disclosed missing Handoff/cards/yesterday's `call-it-a-day`, verified the probe, kept the current session. Disclosed incomplete session details ("indice delle sessioni non disponibile") — see C14-CLAUDE-01. **Passed with degradation.** |
| Study later | native | `/study-later` appended one innocuous topic; log row matches. **Passed.** |
| Checkpoint | native | Created the card: `provider=claude`, revision 1, native ID, folder, state `active`, timestamp `2026-11-13T09:59:59+00:00` (no format hint given). Added read-only Check `probe content`; `deskmate check` → ok. `session-delta` recognized the boundary (`coverage.origin=checkpoint`, full, no warnings). **Passed.** |
| Same-Provider resume | native | Fully exited (exit 0, `session-end`). `deskmate work-session --dry-run` **refused** (`session_unavailable`) before and after exit — C14-CLAUDE-01. Resumed with native `claude --resume <id>`: same ID in the new `session-start`, same folder. The resumed `/checkpoint` confirmed ID/folder/ownership/Check and wrote revision 2 (`2026-11-13T10:01:46+00:00`). **Native resume passed; Deskmate resume routing failed.** |
| Selected retrospective | native | `/how-did-it-go` ran `deskmate retrospective` (durable evidence, three candidates, no message reads) and paused for selection. After explicitly selecting only `85b0fc6e…`, it read the bounded delta from the revision-2 Checkpoint (limits 12 messages/6,000 chars; 4 messages included at that time, 0 omitted, full coverage, no warnings) and disclosed the unread sessions. Candidate metadata carried `Session index unavailable; transcript metadata not read.` **Passed with degradation.** |
| Lessons | native | After operator agreement on the three proposed experiments, appended the Italian retrospective to `lessons.md`. **Passed.** |
| Evening | native | `/call-it-a-day` ran the live Check (ok, 11:04), wrote `handoff.md` for Monday 2026-11-16 with Provider, native ID, folder, the Deskmate resume command plus the native `claude --resume` fallback while C14-CLAUDE-01 is open, and the unread sessions as gaps. No previous Handoff to archive; the operator declined new study topics. **Passed.** |

The coordinator re-ran the public retrospective commands; outputs are in the JSON
evidence. All files tracked in the source index are unchanged.

## Open finding: C14-CLAUDE-01

`adapter_claude.resume_available` (and Claude session metadata) relies only on
`<config>/projects/*/sessions-index.json`. Claude Code 2.1.323 did not create that
file in the isolated configuration at any point (live, after full exit, after
resume); only `<id>.jsonl` transcripts exist. First observation, with the
session live, card revision 1 owned by `claude:85b0fc6e…`:

```text
$ deskmate work-session --folder …/project --dry-run
Cannot resume claude: session_unavailable. Ownership is unchanged.
Choose an explicit new Work session with --new --provider claude.
```

Same output after full exit. Consequences: Deskmate routing cannot resume a
Claude-owned project; `whats-on-today`, `sessions` and `retrospective` report
Claude sessions as degraded; sessions without a cached usage snapshot have no
metrics. Native `claude --resume` works. Not fixed here (test-only session).
Whether an index appears in a non-isolated or older configuration was not tested.

## Authentication — first observations and workaround

1. With only HOME isolated, onboarding showed `Select login method`. macOS showed
   a **"Keychain Not Found" dialog (Cancel / Reset To Defaults)** because the login
   keychain is looked up under `$HOME/Library/Keychains`. The operator was told to
   press Cancel, never Reset To Defaults.
2. Session `b69d73d3-6bad-4b8a-ba7c-3d0421c1db64`: two Ctrl+C at onboarding reached
   the prompt unauthenticated; `/exit` exit 0. Its native session-start/end hooks
   were logged with Claude attribution although no model request was possible.
3. A restart with `CLAUDE_CONFIG_DIR` set still asked for login; the operator
   interrupted it at the login menu.
4. Session `ea3fe3ce-83bd-48bc-b365-74b83834ad74`: header showed `API Usage
   Billing`, but `/setup` returned `Not logged in · Please run /login`. Only
   session-start/end were logged.
5. **Workaround (owner-approved):** temporary symlink
   `home/Library/Keychains → ~/Library/Keychains`, without `CLAUDE_CONFIG_DIR`.
   Created 09:55:56Z, removed 10:06Z after the last native process exited. The
   session authenticated as `Claude Team` without login. No credential value was
   read, printed or stored; the isolated `.credentials.json` is 2 bytes.

## Limits and other observations

- **Approvals:** Claude Code 2.1.323 started in its default **auto** permission
  mode with a notice that organization configuration may apply. No manual
  permission prompt appeared; tool calls showed `Allowed by auto mode`. No bypass
  flag or `bypassPermissions` was used, but manual approval prompts were not
  exercised. Folder trust was recorded as accepted in the isolated `.claude.json`
  without a trust dialog seen by the coordinator (possibly during the Ctrl+C
  onboarding exit of `b69d73d3`).
- Claude-only setup created `home/.codex/.deskmate-integration.lock` although
  Codex was excluded (minor side effect).
- Claude Code itself installed a native copy, `~/.local/bin/claude` and a URL
  handler app inside the isolated HOME.
- The retrospective described the idle unauthenticated `ea3fe3ce` as "33 minuti
  di lavoro"; durable evidence alone could not tell (minor wording).
- The Handoff says the dry-run output was not recorded: true inside the test
  session; the coordinator recorded it here.

## Not verified

- Cross-Provider group (suspended) and C14-CODEX-02 (open).
- Desktop (`mac`) reminders and calendar import: channels disabled.
- iTerm launch submission via `deskmate work-session`: routing refused
  (C14-CLAUDE-01), so resume used the native CLI directly.
- Manual (non-auto) permission prompts and a visible folder-trust dialog.

The shared tracker and C14 checkboxes were not changed (owned by the Codex
coordinator). No implementation change, push or merge.

## Coordinator status reconciliation

The Claude report above records its isolated source snapshot. C14-CODEX-02
was separately triaged as a documented bounded runtime limitation; see the
[SQLite investigation](c14-codex-sqlite-2026-11-13.md). It no longer awaits
initial triage. The latest automated suite remains 255/255 passed in the original
feature worktree. The Codex coordinator compared the actual hook CSV against
this report's JSON (identical), confirmed removal of the temporary Keychain
symlink, and repeated the public resume dry-run: exit 4, `session_unavailable`.
C14-CLAUDE-01 remains open. No implementation repair or new native request
was performed during this status check.

## Resume repair follow-up

C14-CLAUDE-01 eligibility/discovery is repaired after the source snapshot above;
see the [repair evidence](c14-claude-resume-fix-2026-11-13.md). The actual native
fixture dry-run now succeeds. Repaired terminal submission and remaining native
acceptance are separate checks; C14 is still open.

The subsequent [real Deskmate resume](c14-claude-native-resume-2026-11-13.md)
now verifies actual terminal submission, matching native identity and full exit,
with the isolated transport adaptation recorded explicitly.
