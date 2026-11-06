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

3. **Refresh.** The handoff is a snapshot of last evening. Run `python3 -I ~/Dev/mc_dev/deskmate/tools/check.py`: it runs the read-only checks listed in each project card, except the standby ones (listed on its last line). For items that depend on other people or on external state (approvals, PRs, CI, pending replies) and have no check in the card, check them with a command. Done when every "Waiting on" has a state from this morning. Do not use Slack (no searches, no channel or DM reads): for replies awaited on Slack, report the state written in the handoff and let the user check.

4. **What changed on the remote.** Before proposing work, collect the repositories named by the active/paused cards' Checks and work folders; deduplicate by canonical repository root. Use the existing card discovery, not another provider-specific card path. Exclude standby projects unless the user asked to resume them.
   - For each repository, use the remote integration/default branch named by the card. Otherwise resolve the configured remote's symbolic default (for `origin`: `git -C <repo> symbolic-ref --short refs/remotes/origin/HEAD`). If no branch can be established, report the gap instead of assuming `develop` or using the local branch. A repo without a `git -C` Check needs one read-only fetch before its remote report. If a fetch fails, label cached results and remote freshness unknown.
   - Use the Handoff's creation timestamp as the lower bound, not the future date in its title. Prefer its `Generated:` metadata; for older files use the modification timestamp, labeled estimated. Show commits with hash, author, timestamp and subject, e.g. `git -C <repo> log <remote>/<branch> --since=<timestamp> --format='%h %aI %an <%ae> %s'`. Quote shell arguments. Compare author email with `git config user.email` (name only if email is unavailable) and mark known other authors as **others**; if identity is unknown, say so.
   - When `gh` is available, ask it for PRs merged in the same interval, with explicit repository identity (`gh pr list --repo <owner/repo> --state merged --search 'merged:>=<date>' --limit 100 --json number,title,author,mergedAt,url`), then filter `mergedAt` against the precise Handoff timestamp. Follow pagination when the result limit is reached; disclose incomplete coverage. An unavailable CLI, authentication or network does not suppress commit results: report PR coverage as unavailable. Fetch/read commands here inspect repositories and PRs only; they do not search Slack.
   - **Reconcile first:** when a remote commit or merged PR contradicts the Handoff's To do, say what is already done, verify the relevant remote ticket/PR state, and remove it from the proposed work. Report conflicts/unknowns before the order of the day.
   - Across all successfully checked repositories with no new commits/PRs, print one combined line, "Nothing new on the remote", translated into `language`. Do not print it once per repo; when any freshness or PR coverage is unknown, qualify the result and list the gaps. With no active repositories, say that instead of claiming an empty remote window.

5. **Propose the day.** In chat, short:
   - **Before you start:** the preparation steps from the handoff.
   - **In stand-by:** the projects in state `standby`, in one line. Do not propose them and do not open sessions for them unless the user asks; if they do, run their checks with `check.py <card>`.
   - **Suggested order:** first what unblocks others (messages to send, replies to give), then the long work.
   - **Method:** the running experiments from `lessons.md`, one line each, to keep them in mind.
   - The number of open items in `study-later.md`, without listing them: they are for after closing time.
   - **Experiment running:** if `config.json` has `experiments.fresh_sessions`, always add this reminder: "We are collecting data on <question>: today is a **resume** day / a **new session** day" (new on the weekdays in `new_days`, resume on the others), with the count so far from the "per mode" lines of `python3 -I ~/Dev/mc_dev/deskmate/tools/session_stats.py` (e.g. "resume 3/5, new 2/5"). When both modes reach `target_days`, say that the next `/how-did-it-go` will decide.
   - **What you can use:** one line per deskmate command, from the `description` in `~/Dev/mc_dev/deskmate/skills/*/SKILL.md`, translated into `language`, plus the line "`/checkpoint` at the end of each work session, so tonight's handoff is ready". If `git -C ~/Dev/mc_dev/deskmate log --since=<date of the previous whats-on-today in log.csv>` shows new commits, add one line "New:" with what they changed for the user.

6. **Open the sessions.** Ask which ones to open (not the standby ones, unless the user names them), proposing a tab title for each, and open each one in its own iTerm tab. If a check of that project failed on something its "Before you start" asks for (an SSH key not loaded, a login expired, a service off), ask the user to do it first and open the session only after, rerunning the check:

   ```bash
   ~/Dev/mc_dev/deskmate/tools/open_tab.sh "<title>" <folder> <id>
   ```

   The title is `<project> <ticket> · <what to do>`: the short project name and ticket from the handoff heading, then the first "To do" in 2–3 words, in `language` (e.g. `Basler CAT-207 · test camera`, `vlm WRKR-347 · fix review`). Without a ticket, leave it out (`Artisan · grilling`).

   On a **new session** day of the experiment, open the project's work with `open_tab.sh --new "<title>" <folder> "<prompt>"` instead: a fresh session in the same folder, started with a prompt in `language` asking it to pick up from the project card (read the Status, run the Checks, say where to start). Only for projects whose card has a `## Status` from `/checkpoint`; the others are resumed, and you say why.

   If the session is already running in a tab, the script brings that tab to the front instead of opening a second one. If an ID does not open, suggest `claude --resume` from the session's folder to pick it from the list.
