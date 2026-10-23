---
name: setup
description: Installs or health-checks deskmate on this Mac (skills, hooks, reminders) and verifies everything responds.
disable-model-invocation: true
---

# Setup

Prepares the Mac for the deskmate skills, or runs a health check if it is already installed. Speak in the user's language (from `data/config.json` if it exists, otherwise the language they write in); they should not need to know launchd or hooks to understand the outcome.

## Steps

1. **Location.** The repo must live in `~/Dev/deskmate`: the skills look for data and scripts there. If the current folder is elsewhere, offer to move it and stop until it is in place.

2. **Preferences.** If `data/config.json` exists, show `name` and `language` and ask whether to keep them. Otherwise ask for the name to be called by and the language for replies, handoffs and reminders (`en` or `it`; any other language works for Claude's replies, while the reminders fall back to English).

3. **Install.** Run `./install.sh --name <name> --language <language>` from the repo root and read the output. Every `✗` blocks: explain what is missing and how to install it (for example `brew install jq`), then run it again. Every `!` is a warning: report it with one sentence on what it means.

4. **Verify.** Check that every piece actually responds, not just that it exists:
   - the 4 day skills are links to `skills/` in this repo: `ls -l ~/.claude/skills`;
   - the hooks are in `~/.claude/settings.json`: `jq .hooks ~/.claude/settings.json`;
   - the hook scripts work: pipe a test JSON to `tools/hook_log.sh` (`{"prompt":"/study-later test","session_id":"verify","cwd":"/"}`), check that the row appears in `data/log.csv`, then remove it;
   - the reminders are loaded: `launchctl print gui/$(id -u)/com.deskmate.morning` and `.../com.deskmate.evening`;
   - the reminder text is in the right language: `DESKMATE_DRY_RUN=1 tools/evening_reminder.sh`.
   Done when every item has an observed result.

5. **Summary.** In chat, one line per piece with ✓ or the remaining problem. Remind the user that Claude sessions already open see the hooks only after a restart, and that the typical day is: `/whats-on-today` in the morning, `/study-later` during the day, `/how-did-it-go` (Mon, Wed, Fri) and `/call-it-a-day` around 17:00.

To remove everything: `./install.sh --remove` (data stays).
