---
name: whats-on-today
description: Start of the day - rereads the handoff, checks what changed and reopens the sessions.
disable-model-invocation: true
---

# What's on today

Get the user back on track in a few minutes, starting from the handoff written by `/call-it-a-day`. Data files live in `~/Dev/mc_dev/deskmate/data/`. First read `~/Dev/mc_dev/deskmate/data/config.json`: address the user by `name` and write every reply in `language`. Short sentences, plain words.

## Steps

1. **Read.** `~/Dev/mc_dev/deskmate/data/handoff.md` and the experiments of the latest entry in `~/Dev/mc_dev/deskmate/data/lessons.md`. If the handoff is not from the previous working day, say so and offer to rebuild it with `python3 -I ~/Dev/mc_dev/deskmate/tools/sessions.py --since <date>`.

2. **Missed steps.** In `~/Dev/mc_dev/deskmate/data/log.csv`, check the previous working day: is there a `call-it-a-day`? If it was Monday, Wednesday or Friday, is there a `how-did-it-go`? The `morning-reminder` and `evening-reminder` rows tell whether the alert arrived and how the user answered. Report only what is missing, in one line.

3. **Refresh.** The handoff is a snapshot of last evening. For every item that depends on other people or on external state (approvals, PRs, CI, pending replies), check its current state with a command. Done when every "Waiting on" has a state from this morning. Do not use Slack (no searches, no channel or DM reads): for replies awaited on Slack, report the state written in the handoff and let the user check.

4. **Propose the day.** In chat, short:
   - **Before you start:** the preparation steps from the handoff.
   - **Suggested order:** first what unblocks others (messages to send, replies to give), then the long work.
   - **Method:** the running experiments from `lessons.md`, one line each, to keep them in mind.
   - The number of open items in `study-later.md`, without listing them: they are for after closing time.

5. **Open the sessions.** Ask which ones to open, proposing a tab title for each, and open each one in its own iTerm tab:

   ```bash
   ~/Dev/mc_dev/deskmate/tools/open_tab.sh "<title>" <folder> <id>
   ```

   The title is `<project> <ticket> · <what to do>`: the short project name and ticket from the handoff heading, then the first "To do" in 2–3 words, in `language` (e.g. `Basler CAT-207 · test camera`, `vlm WRKR-347 · fix review`). Without a ticket, leave it out (`Artisan · grilling`).

   If an ID does not open, suggest `claude --resume` from the session's folder to pick it from the list.
