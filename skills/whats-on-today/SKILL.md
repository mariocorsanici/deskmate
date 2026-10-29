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

3. **Refresh.** The handoff is a snapshot of last evening. Run `python3 -I ~/Dev/mc_dev/deskmate/tools/check.py`: it runs the read-only checks listed in each project card. For items that depend on other people or on external state (approvals, PRs, CI, pending replies) and have no check in the card, check them with a command. Done when every "Waiting on" has a state from this morning. Do not use Slack (no searches, no channel or DM reads): for replies awaited on Slack, report the state written in the handoff and let the user check.

4. **Propose the day.** In chat, short:
   - **Before you start:** the preparation steps from the handoff.
   - **Suggested order:** first what unblocks others (messages to send, replies to give), then the long work.
   - **Method:** the running experiments from `lessons.md`, one line each, to keep them in mind.
   - The number of open items in `study-later.md`, without listing them: they are for after closing time.
   - **Experiment running:** if `config.json` has `experiments.fresh_sessions`, always add this reminder: "We are collecting data on <question>: today is a **resume** day / a **new session** day" (new on the weekdays in `new_days`, resume on the others), with the count so far from the "per mode" lines of `python3 -I ~/Dev/mc_dev/deskmate/tools/session_stats.py` (e.g. "resume 3/5, new 2/5"). When both modes reach `target_days`, say that the next `/how-did-it-go` will decide.
   - **What you can use:** one line per deskmate command, from the `description` in `~/Dev/mc_dev/deskmate/skills/*/SKILL.md`, translated into `language`, plus the line "`/checkpoint` at the end of each work session, so tonight's handoff is ready". If `git -C ~/Dev/mc_dev/deskmate log --since=<date of the previous whats-on-today in log.csv>` shows new commits, add one line "New:" with what they changed for the user.

5. **Open the sessions.** Ask which ones to open, proposing a tab title for each, and open each one in its own iTerm tab. If a check of that project failed on something its "Before you start" asks for (an SSH key not loaded, a login expired, a service off), ask the user to do it first and open the session only after, rerunning the check:

   ```bash
   ~/Dev/mc_dev/deskmate/tools/open_tab.sh "<title>" <folder> <id>
   ```

   The title is `<project> <ticket> · <what to do>`: the short project name and ticket from the handoff heading, then the first "To do" in 2–3 words, in `language` (e.g. `Basler CAT-207 · test camera`, `vlm WRKR-347 · fix review`). Without a ticket, leave it out (`Artisan · grilling`).

   On a **new session** day of the experiment, open the project's work with `open_tab.sh --new "<title>" <folder> "<prompt>"` instead: a fresh session in the same folder, started with a prompt in `language` asking it to pick up from the project card (read the Status, run the Checks, say where to start). Only for projects whose card has a `## Status` from `/checkpoint`; the others are resumed, and you say why.

   If the session is already running in a tab, the script brings that tab to the front instead of opening a second one. If an ID does not open, suggest `claude --resume` from the session's folder to pick it from the list.
