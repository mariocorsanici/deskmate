---
name: whats-on-today
description: Start of the day - rereads the handoff, checks what changed and reopens the sessions.
disable-model-invocation: true
---

# What's on today

Use the same skill in either Provider: `/whats-on-today` in Claude Code, `$whats-on-today` in Codex CLI. References to other skills use that same native prefix. Resolve `<data>` from `DESKMATE_DATA_DIR` (expand `~` and resolve relative paths from the invocation directory), otherwise `<repo>/data`. Resolve `<repo>` from the real target of the installed `deskmate` command (its parent is `bin/`), or use the current repository before installation. Read and write all personal files under that root. Use the installed `deskmate` command; before installation, use the repository’s `bin/deskmate`.

Get the user back on track in a few minutes, starting from the handoff written by `/call-it-a-day`. Data files live in `<data>/`. First read `<data>/config.json`: address the user by `name` and write every reply in `language`. Short sentences, plain words.

## Steps

1. **Read.** `<data>/handoff.md` and the experiments of the latest entry in `<data>/lessons.md`. If the handoff is not from the previous working day, say so and offer to rebuild it from shared cards and `deskmate sessions --provider all --since <date> --messages 0 --format json`; inspect only missing progress through `deskmate session-delta --provider <claude|codex> --session-id "<id>" --format json`, disclosing coverage and truncation.

2. **Missed steps.** In `<data>/log.csv`, check the previous working day: is there a `call-it-a-day`? If it was Monday, Wednesday or Friday, is there a `how-did-it-go`? The `morning-reminder` and `evening-reminder` rows tell whether the alert arrived and how the user answered. Report only what is missing, in one line.

3. **Refresh.** The handoff is a snapshot of last evening. Run `deskmate card list` and read the latest `## Status` in each shared card; refresh the handoff state from any newer Checkpoint before proposing the day. Report discovery errors. Run `deskmate check`: it runs the read-only checks listed in each project card, except the standby ones (listed on its last line). For items that depend on other people or on external state (approvals, PRs, CI, pending replies) and have no check in the card, check them with a command. Done when every "Waiting on" has a state from this morning. Do not use Slack (no searches, no channel or DM reads): for replies awaited on Slack, report the state written in the handoff and let the user check.

4. **Propose the day.** In chat, short:
   - **Before you start:** the preparation steps from the handoff.
   - **In stand-by:** the projects in state `standby`, in one line. Do not propose them and do not open sessions for them unless the user asks; if they do, run their checks with `deskmate check <card>`.
   - **Suggested order:** first what unblocks others (messages to send, replies to give), then the long work.
   - **Method:** the running experiments from `lessons.md`, one line each, to keep them in mind.
   - The number of open items in `study-later.md`, without listing them: they are for after closing time.
   - **Experiment running:** if `config.json` has `experiments.fresh_sessions`, report today's resume/new mode and previously saved measurements with their Provider and date. Keep historical Claude-only measurements separate. If mode counts or native metrics are missing, say unavailable and keep collecting; opening the day does not authorize scanning conversation history. When saved evidence establishes both modes reached `target_days`, say the next retrospective will decide.
   - **What you can use:** one line per deskmate command, from the `description` in `<repo>/skills/*/SKILL.md`, translated into `language`, plus the line "`/checkpoint` at the end of each work session, so tonight's handoff is ready". If `git -C "<repo>" log --since=<date of the previous whats-on-today in log.csv>` shows new commits, add one line "New:" with what they changed for the user.

5. **Open the sessions.** Ask which ones to open (not the standby ones, unless the user names them), proposing a tab title for each, and open each one in its own iTerm tab. If a check of that project failed on something its "Before you start" asks for (an SSH key not loaded, a login expired, a service off), ask the user to do it first and open the session only after, rerunning the check:

   ```bash
   deskmate work-session --folder "<folder>" --title "<title>"
   ```

   The title is `<project> <ticket> · <what to do>` in `language`. Normal continuation uses the card's recorded Provider and native ID; an unowned project uses the Default provider. A submitted tab is pending until a matching native hook confirms ownership. If the command refuses because the recorded Provider or session is unavailable, present its reason and choices, then wait for an explicit choice. Use `deskmate work-session --folder "<folder>" --new --provider <claude|codex>` for a deliberate fresh start; use `deskmate switch --folder "<folder>" --to <claude|codex> --preview` when continuity across Providers is needed. Show its preview and run the interactive switch only after the user chooses it; its terminal consent remains required.

   On a **new session** day, only for a project with a saved Checkpoint, use `deskmate work-session --folder "<folder>" --new --provider <recorded-provider> --title "<title>" --prompt "<prompt>"`. Take the Provider from the card; use the Default provider only for unowned work. Ask the new session to read the card, run Checks and state where to start. Other projects resume, explaining why. An already running Claude tab may be focused; native availability failures remain explicit choices.
