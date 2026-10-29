---
name: checkpoint
description: End of a work session - writes where the project stands in its project card, so /call-it-a-day reads it instead of the transcript.
disable-model-invocation: true
---

# Checkpoint

Run inside a project's work session, when you stop working on it (at the end of the day, or before switching project). It replaces "give me a recap": the state goes in the **project card**, the one place that `/call-it-a-day`, `/whats-on-today` and the next session of this project all read. First read `~/Dev/mc_dev/deskmate/data/config.json`: address the user by `name` and write your reply in `language`; the card stays in English.

## Steps

1. **Find the card.** It is `~/.claude/projects/<folder-key>/memory/project-card.md`, where `<folder-key>` is the folder this session started in with every character that is not a letter or a digit replaced by `-` (e.g. `~/Dev/domyn-dev/vlm-demo-builder` → `-Users-<user>-Dev-domyn-dev-vlm-demo-builder`). If it does not exist, create it with a memory frontmatter (`name: project-card`, a one-line `description`, `type: project`), a title with the project's short name and ticket, and a few lines on where the work happens: machine, folder, branch, reference docs. Add a pointer to it in that folder's `MEMORY.md`.

2. **Session ID.** Take it from the latest `checkpoint` row in `~/Dev/mc_dev/deskmate/data/log.csv` (column `session`): the hook writes it when this command starts.

3. **Check before writing.** Every fact that a command can confirm (branch, commits ahead of origin, uncommitted files, PR state, CI, services running) is checked now, not taken from memory of the conversation.

4. **Write the status.** Replace the `## Status` section of the card (add it if missing) with:

   ```markdown
   ## Status
   Checkpoint <YYYY-MM-DD HH:MM>, session `<session-id>`, folder `<folder>`.
   - **State:** active | paused | closed
   - **Where you are:** facts, with numbers (tests, PRs, commits, what is not committed or not pushed)
   - **To do:** concrete actions in order, the first in bold
   - **Waiting on:** who or what, or "nothing"
   - **Before you start:** preparation steps (SSH keys, VPN, services), or "nothing"
   ```

   `paused` means the work waits for a decision about priorities; `closed` means nothing is left to do, and `/call-it-a-day` will list it only among the work closed today. If the card has an older progress paragraph that this section now covers, remove it: the status lives in one place.

5. **Checks.** Make sure the card has a `## Checks` section listing the read-only commands that tell, in a few seconds, whether the state above is still true. One per line, as `- <label>: \`<command>\``, for example:

   ```markdown
   ## Checks
   - branch: `git -C ~/Dev/domyn-dev/vlm-demo-builder status -sb | head -1`
   - PR #40: `gh pr view 40 -R igeniusai/vlm-demo-builder --json state -q .state`
   - advrob01: `ssh -o ConnectTimeout=5 -o BatchMode=yes advrob01-ubuntu true`
   ```

   Only commands that change nothing: no fetch with side effects beyond refs, no writes, no Slack. Run `~/Dev/mc_dev/deskmate/bin/deskmate check <card>` to confirm they work, and fix the ones that fail for the wrong reason.

6. **Resume rating.** If `config.json` has `experiments.fresh_sessions` and this is the first checkpoint of the day for this session, ask one question: "How did the restart go this morning? **1** picked up straight away · **2** I had to explain something again · **3** it worked on stale or wrong context". Record the answer with `~/Dev/mc_dev/deskmate/bin/deskmate log-event resume-rating <1|2|3> <session-id> <folder>`. Skip it if the user does not want to answer.

7. **Reply.** In chat, the status as written (translated into `language`) and one line: "Saved in the project card, `/call-it-a-day` will use it."
