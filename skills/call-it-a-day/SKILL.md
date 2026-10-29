---
name: call-it-a-day
description: End of the day - snapshots the open Claude sessions and writes the handoff for tomorrow.
disable-model-invocation: true
---

# Call it a day

Leave tomorrow's user a **handoff**: for every open piece of work, where it stands, what is left to do and how to resume it. Data files live in `~/Dev/mc_dev/deskmate/data/`. First read `~/Dev/mc_dev/deskmate/data/config.json`: address the user by `name`, and write every reply and the handoff in `language`. Short sentences, plain words, jargon explained.

## Steps

1. **Retrospective.** If today is Monday, Wednesday or Friday and `~/Dev/mc_dev/deskmate/data/lessons.md` has no entry for today yet, ask whether to run `/how-did-it-go` first. If yes, stop here: the user will run this skill again afterwards.

2. **Collect.** The state of each project comes from its **project card**, written by `/checkpoint` in the project's own session: `~/.claude/projects/*/memory/project-card.md`, section `## Status`. Then run `~/Dev/mc_dev/deskmate/bin/deskmate sessions` (today's sessions) to see which sessions were active, and reread `~/Dev/mc_dev/deskmate/data/handoff.md`.
   - **Card with a checkpoint later than the session's last activity:** use the card as it is, without reading the transcript.
   - **Session active after its last checkpoint, or without a card:** read its last messages (`--messages 40` if needed) and suggest running `/checkpoint` there next time. List these sessions in the sign-off.
   - Skip this session and the ones that only ran deskmate skills.
   - Work in the previous handoff that was not touched today stays, marked "not touched today".
   Done when every piece of work is classified as **open** (state `active` or `paused`, or something left to do or to wait for) or **closed** (state `closed`, goes only in the summary).

3. **Check live state.** Run `~/Dev/mc_dev/deskmate/bin/deskmate check`: it runs the read-only checks listed in each card and prints one line per check. Write the results in the handoff with the time, and where a check contradicts the card, trust the check and say so. For items with no check in the card, check them by hand with a command. Do not use Slack (no searches, no channel or DM reads): Slack messages go in the handoff only if they appear in the cards or in the session transcripts. Done when no item reports a state that could have been checked and was not.

4. **Write.** Move the old `handoff.md` to `archive/YYYY-MM-DD.md` (the date in its title), then write the new one in this shape, with the headings translated into `language`:

   ```markdown
   # Handoff for <weekday> <date>

   ## In short
   - one line per open session: name, what unblocks it

   ## 1. <Name of the work>
   Resume: `cd <folder> && claude --resume <id>` (from the card's checkpoint line)
   - **Where you are:** facts, with numbers where available (tests, PRs, commits)
   - **To do:** concrete actions, the first in bold
   - **Waiting on:** who or what, if anyone
   - **Before you start:** preparation steps (SSH keys, VPN, services to start), if needed

   ## Closed today
   - one line per finished piece of work
   ```

5. **Study later.** Suggest up to 5 topics met today that are worth studying calmly: concepts explained in a hurry, solutions adopted without fully understanding them, new tools. The user picks; add the chosen ones to `~/Dev/mc_dev/deskmate/data/study-later.md` in the `/study-later` format.

6. **Sign off.** Short message in chat:
   - how many sessions are still open and the first thing to do tomorrow;
   - the sessions read from the transcript because they had no fresh checkpoint, if any;
   - **After closing:** 2 or 3 open items from `study-later.md` that fit the time left, plus any admin tasks that came up today.
