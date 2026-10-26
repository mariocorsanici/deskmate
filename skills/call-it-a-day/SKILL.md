---
name: call-it-a-day
description: End of the day - snapshots the open Claude sessions and writes the handoff for tomorrow.
disable-model-invocation: true
---

# Call it a day

Leave tomorrow's user a **handoff**: for every open piece of work, where it stands, what is left to do and how to resume it. Data files live in `~/Dev/mc_dev/deskmate/data/`. First read `~/Dev/mc_dev/deskmate/data/config.json`: address the user by `name`, and write every reply and the handoff in `language`. Short sentences, plain words, jargon explained.

## Steps

1. **Retrospective.** If today is Monday, Wednesday or Friday and `~/Dev/mc_dev/deskmate/data/lessons.md` has no entry for today yet, ask whether to run `/how-did-it-go` first. If yes, stop here: the user will run this skill again afterwards.

2. **Collect.** Run `python3 -I ~/Dev/mc_dev/deskmate/tools/sessions.py` (today's sessions). Reread `~/Dev/mc_dev/deskmate/data/handoff.md` too: sessions with open work that were not touched today stay in the handoff, marked "not touched today".
   - Skip this session and the ones that only ran deskmate skills.
   - If the last messages are not enough to understand the state, run it again with `--messages 40` or read the transcript.
   Done when every session is classified as **open** (something left to do or to wait for) or **closed** (finished, goes only in the summary).

3. **Check live state.** The handoff is a snapshot: where an item depends on state you can check with a command (PR, CI, branch, remote service), check it now and write the result with the time. Do not use Slack (no searches, no channel or DM reads): Slack messages go in the handoff only if they appear in the session transcripts. Done when no item reports a state taken only from the transcript that could have been checked.

4. **Write.** Move the old `handoff.md` to `archive/YYYY-MM-DD.md` (the date in its title), then write the new one in this shape, with the headings translated into `language`:

   ```markdown
   # Handoff for <weekday> <date>

   ## In short
   - one line per open session: name, what unblocks it

   ## 1. <Name of the work>
   Resume: `cd <folder> && claude --resume <id>`
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
   - **After closing:** 2 or 3 open items from `study-later.md` that fit the time left, plus any admin tasks that came up today.
