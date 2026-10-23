---
name: setup
description: Installs or health-checks deskmate on this Mac (skills, hooks, reminders) and verifies everything responds.
disable-model-invocation: true
---

# Setup

Prepares the Mac for the deskmate skills, or runs a health check if it is already installed. Speak in the user's language (from `data/config.json` if it exists, otherwise the language they write in); they should not need to know launchd or hooks to understand the outcome.

## Steps

1. **Location.** The repo must live in `~/Dev/deskmate`: the skills look for data and scripts there. If the current folder is elsewhere, offer to move it and stop until it is in place.

2. **Preferences.** `data/config.json` is the single source of truth; this step only edits it. If it exists, show the current values in a short table and ask what to change; otherwise ask for each one:
   - `name`: how Claude addresses the user;
   - `language`: for replies, handoffs, lessons and reminders (`en` or `it`; any other language works for Claude's replies, while the reminder texts fall back to English);
   - `reminders.morning` / `reminders.evening`: times as `HH:MM` (default `09:00` and `17:00`);
   - `reminders.days`: any of `mon`…`sun` (default Monday to Friday);
   - `reminders.channels`, one or more:
     - `mac`: an alert on the Mac; it records the answer, which feeds the *Rhythm* lens of `/how-did-it-go`, but needs the Mac awake;
     - `calendar`: two recurring events with a notification, imported once from a `.ics` file; they reach the phone too and work with the Mac off, but record nothing, and need importing again after changing times or days;
     - `slack`: not available yet (see `ROADMAP.md`).
   Write the answers with `jq` into `data/config.json` (create it as `{}` if missing) and keep any other keys.

3. **Install.** Run `./install.sh` from the repo root and read the output. Every `✗` blocks: explain what is missing and how to install it (for example `brew install jq`), then run it again. Every `!` is a warning: report it with one sentence on what it means.

4. **Verify.** Check that every piece actually responds, not just that it exists:
   - the 4 day skills are links to `skills/` in this repo: `ls -l ~/.claude/skills`;
   - the hooks are in `~/.claude/settings.json`: `jq .hooks ~/.claude/settings.json`;
   - the hook scripts work: pipe a test JSON to `tools/hook_log.sh` (`{"prompt":"/study-later test","session_id":"verify","cwd":"/"}`), check that the row appears in `data/log.csv`, then remove it;
   - with `mac`: the reminders are loaded (`launchctl print gui/$(id -u)/com.deskmate.morning` and `.../com.deskmate.evening`) and their text is in the right language (`DESKMATE_DRY_RUN=1 tools/evening_reminder.sh`);
   - with `calendar`: if the install says the events changed, run `open data/deskmate-reminders.ics` and ask the user to confirm the import in their calendar app; when replacing older events, tell them to delete the previous deskmate events if the app duplicated them.
   Done when every item has an observed result.

5. **Summary.** In chat, one line per piece with ✓ or the remaining problem. Remind the user that Claude sessions already open see the hooks only after a restart, and that the typical day is: `/whats-on-today` in the morning, `/study-later` during the day, `/how-did-it-go` (Mon, Wed, Fri) and `/call-it-a-day` at the evening reminder.

To remove everything: `./install.sh --remove` (data stays).
