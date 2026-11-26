---
name: whats-on-today
description: Start of the day - rereads the handoff, checks what changed and reopens the sessions.
disable-model-invocation: true
---

# What's on today

Before working, read `~/Dev/mc_dev/deskmate/docs/agents/skill-metrics.md` and capture this invocation’s native session/start identity for the completion step.

Get the user back on track in a few minutes, starting from the handoff written by `/call-it-a-day`. Data files live in `~/Dev/mc_dev/deskmate/data/`. First read `~/Dev/mc_dev/deskmate/data/config.json`: address the user by `name` and write every reply in `language`. Short sentences, plain words.

## Steps

0. **Agenda first.** Get today's local date. Read `~/Dev/mc_dev/deskmate/docs/agenda.md`, then run `python3 -I ~/Dev/mc_dev/deskmate/tools/agenda.py list --today <today>` and `python3 -I ~/Dev/mc_dev/deskmate/tools/agenda.py is-dev-day <today>`. Keep the JSON for the brief. Report initialization/repair notices and all invalid-line diagnostics in one short line; exit 2 still provides valid data, and exit 3 takes precedence when a whole day is reserved. On exit 1, explain that agenda availability could not be checked and resolve that before planning development.
   - **Whole non-development day (exit 3):** say so first, naming the commitment; show only the **Non-development** agenda block described in step 5, run this skill's completion step, then finish. Project checks, handoff reconstruction and session opening run only if the user explicitly asks to work anyway.
   - **Half day:** name the reserved half and restrict the development plan to the other half. If both halves have separate entries, say there is no free development slot; propose or open work only on request. These half-day entries still count as development days for `is-dev-day`.

1. **Read and date the Handoff.** Read `~/Dev/mc_dev/deskmate/data/handoff.md` and the latest experiments in `lessons.md`. Establish when the Handoff was written from its `Generated:` ISO timestamp (with timezone offset). For older files without valid metadata, use the file modification time and explicitly call it an estimate; never use the future target date in the heading as creation time. Compute its elapsed age against now. Missing files, unreadable/future timestamps or an unreadable activity log make the age/inactivity assessment unknown; say so and offer to rebuild from sessions rather than inventing evidence.
   - In the local timezone, enumerate complete calendar dates **strictly between** the Handoff's creation date and today. Using `data/log.csv`, count/list those dates with no Deskmate work events: exclude `*-reminder` and `*-end` rows. Include weekends. For each of those dates run `python3 -I ~/Dev/mc_dev/deskmate/tools/agenda.py is-dev-day <date>`: on exit 3 its stdout is the agenda line naming the commitment (archived days included). Never assume travel or leave the agenda does not record. A missing/unreadable log is unknown, not proof that all intervening days were inactive.
   - If at least one intervening date has no work event, open the reply with one line, translated into `language`: "The Handoff was written on <date/time>; it is <elapsed age> old, with <n> days without recorded work in between. Current state comes from today's Checks and remote changes." Name the non-development days among them in the same line, from their agenda entries (e.g. "ieri trasferta Monfalcone"): they explain the gap, but the Handoff is still stale and the live-state rule below still applies. Mention estimated timestamps when applicable. Even if the Handoff targets yesterday, this condition still applies.
   - In that case, derive **Where you are** from live Checks and step 4's remote report. The old Handoff supplies intent (**To do**, **Before you start**); reconcile it against current facts before proposing work. Failed/unavailable checks leave those facts unknown. If the Handoff is not from the previous working day, retain the offer to rebuild it with `python3 -I ~/Dev/mc_dev/deskmate/tools/sessions.py --since <date>`.

2. **Missed steps.** In `~/Dev/mc_dev/deskmate/data/log.csv`, check the previous working day: is there a `call-it-a-day`? The `morning-reminder` and `evening-reminder` rows tell whether the alert arrived and how the user answered. Report only what is missing, in one line.
   For each candidate previous working day, run `python3 -I ~/Dev/mc_dev/deskmate/tools/agenda.py is-dev-day <date>`. Skip dates returning 3, including archived travel days, and continue to the preceding weekday for this missed-steps check. Report invalid-line diagnostics even with exit 3; exit 2 uses valid entries with that warning. This exclusion applies to missed steps; step 1 still checks the handoff's age against the actual previous working day, so a travel day does not make an old handoff current.
   **Retrospective due.** Run `python3 -I ~/Dev/mc_dev/deskmate/tools/retro_due.py --today <today>`. It counts the development days (a `checkpoint` or `call-it-a-day` in the log; whole non-development days in the agenda excluded) since the last `/how-did-it-go`. If `due` is true, the retrospective becomes the first step of the day in step 5, not a missed-step note. Report `agenda_warnings` in one line; on exit 1, say the count is unavailable and do not propose or skip the retrospective on a guess.

3. **Refresh.** The handoff is a snapshot of last evening. Run `python3 -I ~/Dev/mc_dev/deskmate/tools/check.py`: it runs the read-only checks listed in each project card, except the standby ones (listed on its last line). For items that depend on other people or on external state (approvals, PRs, CI) and have no check in the card, check them with a command. Done when every "Waiting on" has a state from this morning. Do not use Slack (no searches, no channel or DM reads).

4. **What changed on the remote.** Before proposing work, collect the repositories named by the active/paused cards' Checks and work folders; deduplicate by canonical repository root. Use the existing card discovery, not another provider-specific card path. Exclude standby projects unless the user asked to resume them.
   - For each repository, use the remote integration/default branch named by the card. Otherwise resolve the configured remote's symbolic default (for `origin`: `git -C <repo> symbolic-ref --short refs/remotes/origin/HEAD`). If no branch can be established, report the gap instead of assuming `develop` or using the local branch. A repo without a `git -C` Check needs one read-only fetch before its remote report. If a fetch fails, label cached results and remote freshness unknown.
   - Use the Handoff's creation timestamp as the lower bound, not the future date in its title. Prefer its `Generated:` metadata; for older files use the modification timestamp, labeled estimated. Show commits with hash, author, timestamp and subject, e.g. `git -C <repo> log <remote>/<branch> --since=<timestamp> --format='%h %aI %an <%ae> %s'`. Quote shell arguments. Compare author email with `git config user.email` (name only if email is unavailable) and mark known other authors as **others**; if identity is unknown, say so.
   - When `gh` is available, ask it for PRs merged in the same interval, with explicit repository identity (`gh pr list --repo <owner/repo> --state merged --search 'merged:>=<date>' --limit 100 --json number,title,author,mergedAt,url`), then filter `mergedAt` against the precise Handoff timestamp. Follow pagination when the result limit is reached; disclose incomplete coverage. An unavailable CLI, authentication or network does not suppress commit results: report PR coverage as unavailable. Fetch/read commands here inspect repositories and PRs only; they do not search Slack.
   - **Reconcile first:** when a remote commit or merged PR contradicts the Handoff's To do, say what is already done, verify the relevant remote ticket/PR state, and remove it from the proposed work. Report conflicts/unknowns before the order of the day.
   - Across all successfully checked repositories with no new commits/PRs, print one combined line, "Nothing new on the remote", translated into `language`. Do not print it once per repo; when any freshness or PR coverage is unknown, qualify the result and list the gaps. With no active repositories, say that instead of claiming an empty remote window.

5. **Propose the day.** In chat, short. Order of the reply: the whole non-development day (step 0, which ends the skill), else the stale-Handoff line (step 1), then the retrospective when due, then the items below in this order.
   - **First: retrospective**, only when step 2 found it due: "`/how-did-it-go`, about 10 minutes: <n> development days since <last_retrospective>" (dates in one line). It comes before the other items, including the preparation steps. The **Method** line below then shows the experiments as they stand before this retrospective; say so.
   - **Before you start:** the preparation steps from the handoff.
   - **In stand-by:** the projects in state `standby`, in one line. Do not propose them and do not open sessions for them unless the user asks; if they do, run their checks with `check.py <card>` (a project name or the card's path).
   - **Non-development** ("Non sviluppo" in Italian), before the suggested order: show today's commitment, tasks from `due`, tasks from `deadline` with the deadline highlighted, `undated` as one count line, and `upcoming` days in one line. Merge a task appearing in both buckets into one line. Keep this block visible on a whole non-development day too.
   - **Goal of the day** ("Obiettivo del giorno"): one sentence, "today <X> matters because <Y>", derived from the handoff and this morning's checks and remote changes: the one result that would make the day count (a deadline, a delivery someone waits for, an unblock). Ask the user to confirm or rewrite it. When they do, log the confirmed text with `~/Dev/mc_dev/deskmate/tools/log_event.sh goal "<text>" "<session-id>" "<starting-folder>"`. No goal on a whole non-development day; on a half day it fits the free half.
   - **Priorities per half day:** for the morning and for the afternoon, one **high** and one **low** priority project: the high one gets the attention, the low one fills the LLM dead times (waiting for a run or a build). Fit them to the goal and to the agenda's reserved halves.
   - **Switches:** a switch to a third project, or swapping high and low, gets one log line with its reason. Show this one-liner once, ready to copy: `! ~/Dev/mc_dev/deskmate/tools/log_event.sh switch "<from> → <to>: <reason>"`.
   - **Logins to do** ("Login da fare" in Italian): run `python3 -I ~/Dev/mc_dev/deskmate/tools/logins.py <project> ...` with today's high and low projects from the priorities above (names or card paths). It checks the cards' `## Logins` read-only and never runs a fix. Show one block with the exact lines to type, one per failing login, as `! <fix>` (e.g. `! gcloud auth login`), so the user does them all now instead of one at a time mid-work. A `warning` (1Password) is a note, not a failure: Touch ID shows up at the first secret read in each terminal; the `!` line unlocks this one, and each work tab will ask again at its first secret read, early rather than mid-task. Report `unavailable`/`unknown` entries in one line: an `unavailable` from a timeout means the state is unknown, not expired, so propose no login for it. If every login is valid, one line saying so; if no proposed card lists logins, say nothing.
   - **Suggested order:** short work that unblocks other work first, then the long work.
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


## Complete the measurement

After completing the steps above, log this skill's end using the identity captured at its start:

```bash
~/Dev/mc_dev/deskmate/tools/log_event.sh whats-on-today-end "" "<session-id>" "<starting-folder>"
```

Follow the completion/unfinished-run rules in `docs/agents/skill-metrics.md`; send the prepared final reply after this last tool action.
