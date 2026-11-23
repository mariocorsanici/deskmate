# Roadmap

Next steps in priority order. Release rules and checklists are in
[docs/agents/release.md](docs/agents/release.md).

## Next

### 1. Install separately from the development checkout
Today the installed copy is the repository in `~/Dev/mc_dev/deskmate`, with
personal data inside it. Install from a clone pinned to a release tag, with
the data in its own folder, so deploy and rollback become "move to tag, rerun
the installer" (`./install.sh`).
- The hooks must receive `DESKMATE_DATA_DIR` too; today only the reminders
  receive it, and hooks fall back to `<repo>/data`.
- Moving existing data is a setup migration with a backup, like the card and
  log migrations.
- Distribution as a Claude Code plugin was set aside because Codex needed its
  own install path. With Codex dropped, compare the plugin with the installer
  before starting: it gives pinned, versioned copies for free.

## Later

### Structured project checks
`## Checks` holds free shell commands, protected only by the read-only
convention, the Provider sandbox and a timeout. Replace or complement them with
structured check types and an allowlist, so Deskmate enforces non-mutating
checks instead of trusting arbitrary shell text.

## Ideas to explore (drafts)

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

- **Codex CLI support:** Deskmate stays a Claude Code tool. The work is parked
  on `feature/codex-cli-support` at `dada99a` (suite green, contains `develop`
  up to `74f713c`); to reopen it, merge the `develop` of that time and follow
  the Codex upgrade checklist in `docs/agents/release.md`.
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
