# Roadmap

Next steps in priority order. Release rules and checklists are in
[docs/agents/release.md](docs/agents/release.md).

## Next

### 1. Try the daily journal by hand for one week
No code. The first step of the journal draft below: keep the morning session
as the journal, write notes in plain words, and count them at the end of the
week. It targets the problems of the trial week (switches never logged, goal of
the day often missing, unfinished evening closes), which matter more day to
day than the installation layout.

Open question to analyse during the week: the day as the frame, the session
as the unit, or **the topic as the unit inside the day** (2026-11-24). A topic
(a PR, a task, a study) groups the sessions that `/clear` creates in the same
tab, for PR and development sessions alike. Candidate designs are in
[DEVELOPMENT-THEMES.md](DEVELOPMENT-THEMES.md), theme 3.

### 2. One way to find the code and the data
A prerequisite for installing anywhere else, whichever way is chosen in item 3.
Today the location is written in many places:

- The skills name `~/Dev/mc_dev/deskmate/...` about fifty times (`tools/` and
  `data/` paths).
- `tools/agenda.py` fixes `DATA` to `<repo>/data`; `retro_due.py` overrides it
  from outside. `usage_log.data_root()` already honours `DESKMATE_DATA_DIR`.
- The hooks honour `DESKMATE_DATA_DIR` (through `usage_log.py`), but
  `install.sh` does not pass it to them; only the reminders receive it, so
  hooks fall back to `<repo>/data`.
- `install.sh` writes into `$root/data` and warns when the repo is not in
  `~/Dev/mc_dev/deskmate`.

Goal: every tool resolves the data through `data_root()`, and the skills call
the tools without knowing where the repository is. Behaviour stays the same
with the current layout.

### 3. Install separately from the development checkout
Install from a copy pinned to a release tag, with the data in its own folder,
so deploy and rollback become "move to tag, rerun the installer".
- Decide first: the data folder (proposal: `~/Library/Application
  Support/deskmate`) and the installed copy (a separate clone outside `~/Dev`,
  or `~/Dev/mc_dev/deskmate` pinned to a tag with only the data moved).
- Compare a Claude Code plugin with the installer: the plugin gives pinned,
  versioned copies for free. It was set aside only because Codex needed its
  own install path.
- Moving existing data is a setup migration with a backup, like the card and
  log migrations.

### 4. Open sessions deterministically
`tools/open_tab.sh` types the launch command into the new iTerm tab with
`write text`. While the shell is still starting, macOS keeps at most 1024 bytes
of a typed line (`MAX_CANON`): a longer command is cut and its newline is lost,
so the session never starts. Seen on 2026-11-24 with a `--new` prompt of 1230
bytes (session `475da0f3`); a shorter prompt in the same call worked.

Goal: a session either opens with its full prompt or the script fails with a
clear error, whatever the prompt length and shell start-up time. Candidate fix:
write the prompt and the launch command to a temporary file and have the tab
run that file, instead of typing them. Add a test with a prompt over 1024 bytes.
Related ideas (tab focus off by default, a "session ready" notification) are in
[DEVELOPMENT-THEMES.md](DEVELOPMENT-THEMES.md).

## Ideas to explore (drafts)

Ideas from conversations and the four development themes they form (project
history, daily journal, roles of sessions and cards, PR review sessions) are in
[DEVELOPMENT-THEMES.md](DEVELOPMENT-THEMES.md). They move here as drafts when
they are ready to explore.

### Daily journal (draft, 2026-11-23)
Not designed yet: an idea from the first trial week, to explore before any
implementation. Evidence from that week: the morning session was reused all
day (2026-11-16), switches were never logged (the `switch` one-liner felt
unnatural), the goal of the day was often missing because assigned work ran
out, and two of five evening closes did not finish.

Idea: one file per lived day, `data/journal/YYYY-MM-DD.md`, holding the whole
day and replacing `handoff.md` and its archive:

- `## Plan`: written by `/whats-on-today` (goal, high/low priorities, order,
  waiting items). The morning session then runs `/clear` and becomes the
  journal, so notes do not carry the morning context.
- `## Journal`: timestamped notes in plain words (blocks, switches with their
  reason, decisions, news, "out of assigned work"), from the journal session
  or a `/note <text>` skill usable in any session.
- `## Close`: written by `/call-it-a-day` (goal outcome and why, what closed,
  what deviated from the plan).
- `## Tomorrow`: the handoff (per project: where you are, to do, waiting on,
  before you start; proposed goal). The morning reads the latest journal that
  has this section, so weekends and travel days need no special case.

Open questions:
- Which events are worth a note; whether energy or mood belongs there.
- Whether the journal tab stays open in practice, or `/note` is enough.
- A close done the next morning must write into the day it closes; a repeated
  close replaces `## Close` and `## Tomorrow` and keeps a backup.
- A tool, not the model, should create the file, replace sections and find the
  latest `## Tomorrow`, so the morning reads only that section.
- Migration: keep the handoff archive as history; keep `handoff.md` as a copy of
  `## Tomorrow` during the transition.
- How it relates to the goal-of-the-day and switch changes from the trial week
  (an explicit "out of assigned work" outcome; switches reconstructed by the
  retrospective instead of logged by hand).

First step: one week by hand (keep the morning session as the journal, notes in
plain words) and count the notes before building anything.

## Dropped

2026-11-23:

- **Structured project checks:** `## Checks` stays free shell text, protected
  by the read-only convention and a timeout. The risk came from running checks
  under a second Provider; with Claude Code only and checks written by the
  user, an allowlist is not worth it.
- **Calendar reminder channel:** never tested with a real calendar; the `mac`
  channel covers daily use.
- **Secret scanning for Provider switches:** depended on Codex support.
- **Codex CLI support:** Deskmate stays a Claude Code tool. The work is parked
  on `feature/codex-cli-support` at `dada99a` (suite green, contains `develop`
  up to `74f713c`); to reopen it, merge the `develop` of that time and follow
  the Codex upgrade checklist in `docs/agents/release.md` as of `35ce1ef`.
- **Cross-provider analytics:** depended on Codex support.

2026-11-16:

- **Linux and Windows support:** Deskmate is a personal macOS tool. Reopen if
  someone else adopts it.
- **Slack reminders:** the `mac` alert covers the need and records the answer;
  a webhook message cannot, and the Slack app may need admin approval.
- **Renaming commands** (`/call-it-a-day`): the names are habits now, and
  renaming after Codex support would touch both Providers.
- **Branch protection and mandatory pull requests:** only CI is kept
  (`.github/workflows/tests.yml`, since 2026-11-23).
- **Versioning the project cards with a local git repo:** it was left to the
  card revisions and backups of Codex support, now dropped too. Design it again
  if card history is missed.
