---
name: setup
description: Install, update or remove Deskmate integrations for Claude Code and Codex CLI, with migration backups and logging verification.
disable-model-invocation: true
---

# Setup

Use the common `deskmate setup` and `deskmate remove` commands. Speak in the
user's language. Run commands from the repository containing this skill; before
installation, its entry point is `python3 -I <repo>/bin/deskmate` or `./install.sh`.

1. **Read preferences.** Data lives in `DESKMATE_DATA_DIR` when set, otherwise
   `<repo>/data`. Read the existing `config.json` there and retain unrelated
   preferences. Report the current name, language and reminder settings. Apply
   requested name/language changes with setup's `--name` and `--language` options.
   For requested reminder changes, edit only `reminders` in that configuration
   after confirming the values. Use `HH:MM`, weekdays `mon` through `sun` and
   channels `mac`, `calendar` or `slack` (Slack is planned). Omit changes when the
   user wants an installation health check only.

2. **Install or update.** Run `./install.sh`, preserving `DESKMATE_DATA_DIR` and
   `CODEX_HOME`. Detection includes every compatible Provider by default. Use
   repeated `--provider claude|codex` only when the user requests a subset.
   With both Providers, ask for the Default provider and pass it explicitly as
   `--default-provider claude|codex`. In automation, add `--non-interactive`;
   both Providers require an explicit default. Report excluded Providers and the
   action suggested by the command. If an old Project card cannot be mapped,
   establish its actual project folder and rerun with `--project /absolute/path`.
   Completion requires exit 0 and the reported backup and verification results.

3. **Verify and explain trust.** Setup tests each installed prompt hook against
   disposable state and checks its Provider/session event. Report those observed
   results as synthetic verification. In Codex, the user reviews and trusts the
   Deskmate definitions in `/hooks`; project trust and command approvals remain
   subject to the runtime. In Claude, review normal project/hook approvals and
   restart existing sessions. Native verification requires a user-authorized
   `/checkpoint` (Claude) or `$checkpoint` (Codex) and the matching Provider and
   session row. When native requests are postponed, leave that check pending.
   The command is linked under `~/.local/bin`; follow setup's new-shell/PATH
   guidance. Calendar changes require import into the user's calendar app.

4. **Removal, when requested.** Run `deskmate remove` or `./install.sh --remove`.
   Data is preserved by default. Interactive purge is a separate default-no
   question and requires the exact confirmation `DELETE`. Non-interactive removal
   uses `--non-interactive` and preserves data; append `--purge-data` only for an
   explicit user request to delete that data. Report the exit status and whether
   personal data was retained or purged.
