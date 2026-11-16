---
name: checkpoint
description: End of a work session - writes where the project stands in its project card, so /call-it-a-day reads it instead of the transcript.
disable-model-invocation: true
---

# Checkpoint

Use the same skill in either Provider: `/checkpoint` in Claude Code, `$checkpoint` in Codex CLI. References to other skills use that same native prefix. Resolve `<data>` from `DESKMATE_DATA_DIR` (expand `~` and resolve relative paths from the invocation directory), otherwise `<repo>/data`. Resolve `<repo>` from the real target of the installed `deskmate` command (its parent is `bin/`), or use the current repository before installation. Read and write all personal files under that root. Use the installed `deskmate` command; before installation, use the repository’s `bin/deskmate`.

Before working, read `<repo>/docs/agents/skill-metrics.md` and capture this invocation’s Provider, native session ID and starting folder for the completion step.

Run inside a project's work session, when you stop working on it (at the end of the day, or before switching project). It replaces "give me a recap": the state goes in the **project card**, the one place that `/call-it-a-day`, `/whats-on-today` and the next session of this project all read. First read `<data>/config.json`: address the user by `name` and write your reply in `language`; the card stays in English.

## Steps

1. **Find the shared card.** Run `deskmate card locate "<project-folder>"` using the folder this Work session started in. The JSON result has `path` and `metadata`; read the document at `path` and retain `metadata.revision` (or `0` if metadata is null). If an existing Claude card is a regular file, run `deskmate card migrate "<project-folder>"` first, then locate again. Stop and report migration conflicts or unsupported schemas. If no card exists, compose a new one with frontmatter (`name: project-card`, a one-line `description`, `type: project`), a project title and the working folder, branch and reference docs. In Claude, keep a pointer in the project's native `MEMORY.md` to `project-card.md`; that legacy path resolves to the shared card through a symlink.

2. **Work session ownership.** Use the current Provider (`claude` or `codex`) and the native session identity captured at this invocation’s start. In Claude, match it to this invocation’s `checkpoint` row in `<data>/log.csv` and verify its folder; never take the globally latest checkpoint row from another session. In Codex, use the session ID supplied by the runtime. If identity cannot be established, do not invent a Checkpoint session ID: report what is missing before writing the status.

3. **Check before writing.** Every fact that a command can confirm (branch, commits ahead of origin, uncommitted files, PR state, CI, services running) is checked now, not taken from memory of the conversation.

4. **Compose the status.** Obtain the current UTC timestamp from the system with `python3 -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat(timespec="seconds"))'`. Copy its ISO 8601 result, including seconds and the numeric offset, into `<timestamp>` below. In a separate temporary UTF-8 candidate file, preserve the card content and replace the `## Status` section of the card (add it if missing) with:

   ```markdown
   ## Status
   Checkpoint <timestamp>, session `<session-id>`, folder `<folder>`.
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
   - local branch and uncommitted files: `git -C ~/Dev/domyn-dev/vlm-demo-builder status --short --branch`
   - remote ticket: `git -C ~/Dev/domyn-dev/vlm-demo-builder show origin/develop:.scratch/example/issues/01-example.md | grep -m1 Status`
   - PR #40: `gh pr view 40 -R igeniusai/vlm-demo-builder --json state -q .state`
   - advrob01: `ssh -o ConnectTimeout=5 -o BatchMode=yes advrob01-ubuntu true`
   ```

   File-reading checks for shared tickets, specifications and completed work read the **remote integration/default branch**, with `git -C <repo> show <remote>/<branch>:<path>`, after the central fetch in `deskmate check`. Choose the branch from the card or repository configuration; `origin/develop` above is an example, not a default for every project. A fetch refreshes refs, not working-tree files. Keep working-tree reads only for local state (uncommitted files, local branches or unpublished work), and label each check `remote` or `local` so its meaning is clear. Shell-quote paths containing spaces; use `$HOME` outside quotes or expand `~` before quoting.

   If fetching fails or the remote ref/path is missing, report remote freshness/state as unavailable. A successful read of an older cached ref does not establish current remote state; preserve that limitation in the card and report.

   Only commands that change nothing: no fetch with side effects beyond refs, no writes, no Slack. Run `deskmate check <candidate-file>` to confirm they work, and fix the ones that fail for the wrong reason.

   **Logins** (optional section, after `## Checks`): the logins this project's work needs, one per line, from `ssh-key <path to the private key>`, `gcloud`, `gcloud-adc`, `1password`. Add one when this session hit an expired or missing login, after asking the user; never write a secret, only the type and the key path. `/whats-on-today` checks them every morning with `deskmate logins`.

   Save the complete candidate through:

   ```bash
   deskmate card write "<project-folder>" --expected-revision <revision-read> --provider <claude|codex> --session-id "<current-session-id>" --from "<candidate-file>"
   ```

   Exit `0` confirms the save. The command validates the Status Checkpoint timestamp with the same parser used by Session deltas before publishing. On exit `3`, stdout contains the current card: reread it, reconcile your changes with its Status and Checks, and retry using its current revision. On exit `2`, report the validation or migration error and stop without claiming the card was saved. Write through this command; direct edits through either the shared path or the Claude symlink bypass concurrency protection.

6. **Resume rating.** If `config.json` has `experiments.fresh_sessions` and the Provider plus native ID has no earlier checkpoint today in `<data>/log.csv`, ask one question: "How did the restart go this morning? **1** picked up straight away · **2** I had to explain something again · **3** it worked on stale or wrong context". Record the answer with `deskmate log-event resume-rating <1|2|3> "<session-id>" "<folder>" --provider <claude|codex>`. Skip it if the user does not want to answer.

7. **Reply after a confirmed save (exit `0`).** In chat, the status as written (translated into `language`) and one line: "Saved in the project card, `/call-it-a-day` will use it." If the user says they are leaving this project for another one outside today's high/low pair (or swapping high and low), log it with its reason: `deskmate log-event switch "<from> → <to>: <reason>" "<session-id>" "<starting-folder>" --provider <claude|codex>`.


## Complete the measurement

After completing the steps above, log this skill's end using the identity captured at its start:

```bash
deskmate log-event checkpoint-end "" "<session-id>" "<starting-folder>" --provider <claude|codex>
```

Follow the completion/unfinished-run rules in `<repo>/docs/agents/skill-metrics.md`; send the prepared final reply after this last tool action.
