---
name: checkpoint
description: End of a work session - writes where the project stands in its project card, so /call-it-a-day reads it instead of the transcript.
disable-model-invocation: true
---

# Checkpoint

Run inside a project's work session, when you stop working on it (at the end of the day, or before switching project). It replaces "give me a recap": the state goes in the **project card**, the one place that `/call-it-a-day`, `/whats-on-today` and the next session of this project all read. First read `~/Dev/mc_dev/deskmate/data/config.json`: address the user by `name` and write your reply in `language`; the card stays in English.

## Steps

1. **Find the shared card.** Run `~/Dev/mc_dev/deskmate/bin/deskmate card locate "<project-folder>"` using the folder this Work session started in. The JSON result has `path` and `metadata`; read the document at `path` and retain `metadata.revision` (or `0` if metadata is null). If an existing Claude card is a regular file, run `deskmate card migrate "<project-folder>"` first, then locate again. Stop and report migration conflicts or unsupported schemas. If no card exists, compose a new one with frontmatter (`name: project-card`, a one-line `description`, `type: project`), a project title and the working folder, branch and reference docs. In Claude, keep a pointer in the project's native `MEMORY.md` to `project-card.md`; that legacy path resolves to the shared card through a symlink.

2. **Work session ownership.** Use the current Provider (`claude` or `codex`) and this Work session's ID. In Claude, the matching checkpoint hook row in `data/log.csv` can supply the ID: verify its folder and that it belongs to this session. In Codex, use the session ID supplied by the runtime. If it cannot be established, ask for it; ownership must describe the current Work session.

3. **Check before writing.** Every fact that a command can confirm (branch, commits ahead of origin, uncommitted files, PR state, CI, services running) is checked now, not taken from memory of the conversation.

4. **Compose the status.** In a separate temporary UTF-8 candidate file, preserve the card content and replace the `## Status` section of the card (add it if missing) with:

   ```markdown
   ## Status
   Checkpoint <YYYY-MM-DD HH:MM>, session `<session-id>`, folder `<folder>`.
   - **State:** active | paused | standby | closed
   - **Where you are:** facts, with numbers (tests, PRs, commits, what is not committed or not pushed)
   - **To do:** concrete actions in order, the first in bold
   - **Waiting on:** who or what, or "nothing"
   - **Before you start:** preparation steps (SSH keys, VPN, services), or "nothing"
   ```

   `paused` means the work waits for a decision about priorities, and is still proposed every morning; `standby` means leave it alone until the user asks for it: its checks are not run and the handoff names it in one line only; `closed` means nothing is left to do, and `/call-it-a-day` will list it only among the work closed today. If the card has an older progress paragraph that this section now covers, remove it: the status lives in one place.

5. **Checks and save.** Make sure the candidate has a `## Checks` section listing the read-only commands that tell, in a few seconds, whether the state above is still true. One per line, as `- <label>: \`<command>\``, for example:

   ```markdown
   ## Checks
   - branch: `git -C ~/Dev/domyn-dev/vlm-demo-builder status -sb | head -1`
   - PR #40: `gh pr view 40 -R igeniusai/vlm-demo-builder --json state -q .state`
   - advrob01: `ssh -o ConnectTimeout=5 -o BatchMode=yes advrob01-ubuntu true`
   ```

   Only commands that change nothing: no fetch with side effects beyond refs, no writes, no Slack. Run `~/Dev/mc_dev/deskmate/bin/deskmate check <candidate-file>` to confirm they work, and fix the ones that fail for the wrong reason. Save the complete candidate through:

   ```bash
   ~/Dev/mc_dev/deskmate/bin/deskmate card write "<project-folder>" --expected-revision <revision-read> --provider <claude|codex> --session-id "<current-session-id>" --from "<candidate-file>"
   ```

   Exit `0` confirms the save. On exit `3`, stdout contains the current card: reread it, reconcile your changes with its Status and Checks, and retry using its current revision. On exit `2`, report the validation or migration error and stop without claiming the card was saved. Write through this command; direct edits through either the shared path or the Claude symlink bypass concurrency protection.

6. **Resume rating.** If `config.json` has `experiments.fresh_sessions` and this is the first checkpoint of the day for this session, ask one question: "How did the restart go this morning? **1** picked up straight away · **2** I had to explain something again · **3** it worked on stale or wrong context". Record the answer with `~/Dev/mc_dev/deskmate/bin/deskmate log-event resume-rating <1|2|3> <session-id> <folder>`. Skip it if the user does not want to answer.

7. **Reply after a confirmed save (exit `0`).** In chat, the status as written (translated into `language`) and one line: "Saved in the project card, `/call-it-a-day` will use it."
