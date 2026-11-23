# Roadmap

Next steps in priority order. Release rules and checklists are in
[docs/agents/release.md](docs/agents/release.md).

## Next

### 1. v0.2.0: Agenda and Daily-loop tuning
On `develop`, in daily use for one trial week from 2026-11-16. Fixes go through
`fix/…` branches (`hotfix/…` only for urgent fixes to the installed copy) and
are listed for porting to the Codex branch. After the week, promote `develop`
to `main` and tag `v0.2.0`. No upgrade step.

### 2. v0.3.0: Codex CLI support
`feature/codex-cli-support`: Claude Code and Codex CLI as equivalent
Providers through one `deskmate` command. Follow the upgrade checklist in
`docs/agents/release.md`: bring in `develop` again, port the week's fixes,
rehearse upgrade and rollback in an isolated `HOME`, then `deskmate setup`.
Before tagging, run the integrated skills natively in both Providers (Agenda,
goal of the day, switches, logins, end markers in Codex): today they have
automated coverage only.

### 3. Run the tests in CI
Run the complete suite on pushes and pull requests (GitHub Actions, macOS
runner, Python 3.14 and the system Python), with ResourceWarnings as errors.
Branch protection and mandatory pull requests are not planned: for a single
maintainer they add friction without adding checks.

### 4. Install separately from the development checkout
Today the installed copy is the repository in `~/Dev/mc_dev/deskmate`, with
personal data inside it. After `v0.3.0`, install from a clone pinned to a
release tag, with the data in its own folder, so deploy and rollback become
"move to tag, run `deskmate setup`".
- Setup must pass `DESKMATE_DATA_DIR` to the Claude and Codex hooks too; today
  only the reminders receive it, and hooks fall back to `<repo>/data`.
- Moving existing data is a setup migration with a backup, like the card and
  log migrations.
- Distribution as a Claude Code plugin was considered: it gives pinned,
  versioned copies for Claude, but Codex would still need its own install
  path. `deskmate setup` stays the single install point for both Providers.

## Later

### Cross-provider analytics
After at least a month of use with both Providers. Store Claude Code and Codex
CLI measurements with their Provider identity and analyse them separately
first. Then define normalized metrics that support combined views and explicit
comparisons without mixing incompatible raw token, context or compaction values.

### Structured project checks
`## Checks` holds free shell commands, protected only by the read-only
convention, the Provider sandbox and a timeout. Replace or complement them with
structured check types and an allowlist, so Deskmate enforces non-mutating
checks instead of trusting arbitrary shell text.

### External secret scanning for Provider switches
The switch already applies conservative local redaction and reports what it
removed. As defence in depth, evaluate an optional local scanner that checks
the temporary transfer bundle before either Provider receives it, keeps
findings out of the audit log, falls back to built-in redaction when absent,
and presents findings for explicit review. No scanner can guarantee a bundle
has no secrets; document that.

### Calendar reminders: test the import
The `calendar` channel writes `data/deskmate-reminders.ics` but is
experimental: it has not been imported into a real calendar. Daily use relies
on the `mac` channel. To verify it: import into Google and Apple Calendar,
check that event notifications survive the import, and document what a second
import does after times or days change.

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

## Dropped (2026-11-16)

- **Linux and Windows support:** Deskmate is a personal macOS tool. Reopen if
  someone else adopts it.
- **Slack reminders:** the `mac` alert covers the need and records the answer;
  a webhook message cannot, and the Slack app may need admin approval.
- **Renaming commands** (`/call-it-a-day`): the names are habits now, and
  renaming after `v0.3.0` would touch both Providers.
- **Branch protection and mandatory pull requests:** only CI is kept (step 3).
- **Versioning the project cards with a local git repo:** `v0.3.0` adds card
  revisions and a backup on every overwrite. If card history is still missing
  after that, design it again on the shared cards.
