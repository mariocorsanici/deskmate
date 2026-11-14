# deskmate

Shared skills for Claude Code and Codex CLI to run your working day: open it in the morning, close it in the late afternoon, and every other day take stock of how you work. Deskmate acts as the colleague at the next desk who keeps track of where everything stands.

Use `/skill` in Claude Code and `$skill` in Codex CLI. Setup links the same sources into both. The table uses Claude syntax; substitute `$` in Codex.

## A typical day

| When | Skill | What it does |
|---|---|---|
| morning (reminder) | `/whats-on-today` | rereads the handoff, checks what changed, flags skipped steps, suggests the order of the day, lists the commands you can use and opens the sessions in titled iTerm tabs |
| during the day | `/study-later <topic>` | notes a topic to study later |
| end of each work session | `/checkpoint` | writes where the project stands in its project card |
| Mon, Wed, Fri before closing | `/how-did-it-go` | retrospective on organisation and method, updates `data/lessons.md` |
| evening (reminder) | `/call-it-a-day` | collects the project cards, checks the live state and writes `data/handoff.md` for tomorrow |

After closing: study the topics you set aside, or admin work.

## Project cards

Each project has one shared Markdown card at `data/projects/<slug>-<path-hash>/project-card.md`, independent of Claude or Codex. `DESKMATE_DATA_DIR` overrides the data root. Claude’s existing `~/.claude/projects/<folder-key>/memory/project-card.md` becomes a symlink to that same document. `/checkpoint`, run inside the project's session, keeps two sections of it up to date:

- `## Status`: state (`active`, `paused`, `standby`, `closed`), where you are, what to do, what you are waiting on, how to resume (session ID and folder);
- `## Checks`: read-only commands, one per line as ``- <label>: `<command>` ``, that tell in a few seconds whether the status is still true. `deskmate check` runs them for `/whats-on-today` and `/call-it-a-day`.

`paused` work waits for a decision about priorities and is still proposed every morning. `standby` work is left alone until you ask for it: `deskmate check` skips its checks (unless you pass `--all` or name the card), and the handoff and the morning brief name it in one line. Less noise in the handoff, no slow checks (an SSH timing out on a machine that is off), and a few thousand tokens less per project each day.

`/call-it-a-day` reads the cards instead of the transcripts; it discovers both Providers without reading messages, then reads bounded Session deltas only for work after its matching Checkpoint or without a matching card. Missing history is disclosed and does not block the Handoff.

Use `bin/deskmate card locate <project-folder>` to get its canonical path and metadata as JSON, and `bin/deskmate card list` to discover shared cards. `bin/deskmate card migrate <project-folder>` imports an existing Claude card, preserves an exact content-addressed backup under `data/backups/project-cards/`, and installs the Claude symlink. Repeating migration is safe; differing legacy/shared content stops for explicit resolution.

Writers submit a complete UTF-8 document with `bin/deskmate card write <project-folder> --expected-revision N --provider claude|codex --session-id ID --from FILE`. Use revision `0` for a new card. Updates lock the project, check the revision and atomically replace the document. Exit `3` returns the current card on stdout: reread, reconcile and retry. Invalid metadata or unsupported schemas return `2`. Direct manual edits remain possible for recovery, but bypass revision checks and locking: avoid concurrent manual and automated updates.

Skills call the stable `bin/deskmate` command for Checks, session summaries, statistics, logging and session launch rather than depending on the individual tools that implement them.

Checkpoint skills obtain a UTC ISO 8601 timestamp with seconds from the system.
`card write` validates any Status Checkpoint timestamp with the same parser used
by Session deltas before publishing. Invalid timestamps return exit `2` without
replacing the card or increasing its revision. Existing ISO offsets and legacy
local minute timestamps remain supported; cards without a Checkpoint remain
writable. An invalid older card still produces an explicit warning and a bounded
delta starting at session start.

## Work session routing

`bin/deskmate work-session --folder /path/to/project` continues a Project with
its recorded Provider and native Work session. Claude routing verifies canonical
folder identity using its native index or, when the index is absent, recorded
SessionStart metadata and a unique existing native transcript. A transcript
filename alone cannot prove folder identity, because legacy folder encoding can
collide. Discovery and routing do not read conversation contents. Without an owned Work session,
it starts with the configured Default provider. Add `--dry-run` to inspect the
decision without opening a terminal or changing state; prefix the command with
`--json` for a structured result inside the standard command envelope.

New terminal sessions use the absolute CLI selected in the calling environment,
with explicit HOME, PATH, ZDOTDIR, Codex home and Deskmate data paths. Claude's
`CLAUDE_CONFIG_DIR` is honored when set and remains unset when absent. zsh startup
runs under the selected HOME/ZDOTDIR; verified paths are reapplied before the CLI
starts. The iTerm profile supplies appearance and exit behavior. Its shell cannot
silently select another CLI or native archive. Existing running tabs retain their
own environment when focused.

Deskmate starts and resumes Codex with `--no-daemon`. A shared Codex app server
retains the environment of its first client; reusing it could send native hooks
to another launch's journal or data directory. A dedicated process keeps the
selected paths and launch identity attached to the current Work session without
changing hook trust, sandbox settings or native session storage.

If the recorded Provider or session is unavailable, the command refuses to
silently choose a replacement (exit 4). Make a deliberate new-session choice:

```bash
bin/deskmate work-session --folder /path/to/project --new --provider codex
```

`--provider` requires `--new`; it cannot turn a resume into a Provider switch.
`--title` and `--prompt` supply optional terminal and initial-message text.
This starts a new native Work session. To carry existing progress to another Provider, use the explicit switch preview below.

Opening an iTerm tab submits a command; it does not prove that the native CLI
started. A new session therefore remains `pending` until a matching native
SessionStart or first UserPromptSubmit hook reports its actual ID. Review/trust
Deskmate hooks normally, and rerun `integration --provider claude` or
`integration --provider codex` when installing the lifecycle hooks. Personal
hook commands and matcher groups are preserved. Focusing an already-open Claude
tab reports `focused`, preserves the card and records the existing identity; it
does not wait for a new launch token. Failed submission leaves the
Project card unchanged. Confirmed ownership updates preserve the card's Markdown
and reject stale revisions rather than overwriting a newer Checkpoint.

Per-project `work-sessions.json` journals retain launch attempts and possible
overlap for later switch handling; they contain identity/status metadata, never
prompts or transcript contents. Terminal timeouts/nonzero submission outcomes
remain `uncertain` until clarified; inspect the terminal before retrying. A late
native hook retains identity evidence without changing ownership after a failed
or uncertain submission. SessionEnd closes evidence for the matching Provider,
native ID and canonical folder, including repeated focus attempts. It never
changes ownership. `--dry-run` reports current attempt evidence.
An attempt with `state: conflict` requires rereading the latest card and choosing
how to continue. Interrupted confirmation can retry through the same correlated
native hook, including a confirming write whose card was already published.
Unknown future schemas stop before launch or durable changes. Other failure
codes are 1 (unavailable Provider/terminal launch), 2 (invalid configuration/input)
and 3 (card revision conflict). Daily-loop launch and resume use `work-session`; Provider switches use `switch`.

## Provider switches

```bash
bin/deskmate switch --folder PATH --to claude --preview
bin/deskmate switch --folder PATH --to codex
```

A switch creates a **new** target Work session from the shared Project card,
current Checks and an optional bounded Session delta. The source Provider may be
unavailable. Checks run in the selected Project directory. The preview reports
source/target, card revision, exact bundle bytes, included/omitted context,
coverage, truncation and redaction categories/counts. Common credential formats
are redacted locally; ambiguous recognized multiline/container values block transfer and offer source
review/removal/replacement before a new preview. Redaction is conservative and
does not claim to recognize every possible secret.

Without `--preview`, the command requires a terminal and explicit `yes` consent,
including a warning when another Work session may still be active. There is no
`--yes` or piped-input bypass. Cancellation preserves ownership; a changed card
invalidates the preview. Terminal submission remains pending until matching native
hooks confirm the target's real identity.

Only a private mode-0600 bundle path is passed to the target. Its startup prompt
uses `deskmate transfer-read --bundle PATH --provider claude|codex` to validate and
consume that managed file once. No transferred content is recorded in audit
metadata or launch arguments. Expired bundles cannot be consumed; successful
later normal commands remove valid managed bundles older than one hour. Explicit
previews, dry runs and Session delta reads remain read-only. `deskmate
transfer-cleanup` also performs cleanup directly, preserving fresh/unrelated files
and symlinks. Interrupted writes remain private in reserved staging files; cleanup expires abandoned staging files after one hour while preserving active writers. See [verification and review evidence](docs/testing/provider-switches.md).

## Bounded Session deltas

`deskmate session-delta --provider claude|codex --session-id ID` reads only
conversation text into a bounded Session delta. Claude JSONL, Codex rollout JSONL
and Codex paginated SQLite history use the same selection rules. Metadata,
reasoning, raw tool results and native skill instructions are excluded.

```bash
bin/deskmate session-delta --provider codex --session-id ID
bin/deskmate --json session-delta --provider claude --session-id ID --max-messages 20 --max-characters 10000
```

The default is **12 messages and 6,000 characters**. Set
`session_delta.max_messages` and `session_delta.max_characters` in
`data/config.json` to change the defaults; command flags override them for one
read without changing any data. Limits must be positive integers. The reader
streams records and retains bounded early/recent candidates instead of building
the complete conversation in memory.

The boundary is the saved Checkpoint in the shared Project card, matched to both
the Provider and native session ID. A `/checkpoint` or `$checkpoint` prompt alone
does not prove a successful save. With no matching saved Checkpoint, coverage is
explicitly from session start. Legacy `YYYY-MM-DD HH:MM` Checkpoints assume the
local timezone and have an estimated minute boundary, disclosed as partial
coverage. `--after ISO_TIMESTAMP` supplies a precise boundary with an explicit
timezone. Messages at or before the boundary are excluded; unknown message times
after a known boundary are omitted with a warning.

Selection keeps the first eligible message plus the latest messages. If the
character budget is exceeded, up to half goes to the early message and the rest
to the newest messages. A one-message or one-character budget prefers the latest
message. Text can be clipped within a message; character counts mean Unicode
code points in message text, excluding JSON and display formatting.

Text output reports limits, included/omitted messages and characters, truncation,
coverage and warnings. `--format json` returns a schema-1 result with `provider`,
`id`, `status`, `warnings`, `checkpoint`, `limits`, `messages`,
`included_messages`, `omitted_messages`, `characters`, `omitted_characters`,
`truncated` and `coverage`. The global `--json` option wraps this in Deskmate's
normal envelope and selects JSON content automatically. Counts describe readable,
eligible conversation; skipped corrupt records cannot be counted accurately.
Missing/unreadable history returns exit 0 with `status: degraded` and partial or
unavailable coverage so the Daily loop can continue. Invalid limits/configuration
return exit 2. This command performs local extraction only; `switch` applies redaction, preview and consent before cross-Provider transfer.

Some SQLite runtimes cannot read a closed Codex WAL database after its `-wal`
and `-shm` files have disappeared. This can affect session metadata as well as
paginated history. Deskmate reports unavailable coverage and continues from the
Project card and Checks; it does not repair or rewrite native storage. Reopening
the relevant Codex runtime normally may make the history readable again while
its SQLite sidecars exist. A failed read does not establish that history was
deleted. See the [cold-WAL investigation](docs/testing/c14-codex-sqlite-2026-11-13.md)
for the verified runtime, recovery limits and evidence.

## Experiments

`experiments.fresh_sessions` in `config.json` can select new-session weekdays
with `new_days`; other days resume. Morning uses `work-session --new --provider`
with the recorded Provider for a project that has a Checkpoint. Checkpoint asks
for a 1–3 restart rating and logs its Provider. Morning and retrospective inspect
previously saved measurements, label missing evidence and retain separate native
counters. Historical Claude experiment measurements remain available explicitly
through `deskmate session-stats`; this Claude-only diagnostic scans transcripts
and is outside routine morning/retrospective collection.

## Discovery and retrospective

`deskmate sessions` lists metadata from both Providers by default, without
conversation text. Use `--provider claude|codex|all`, `--since YYYY-MM-DD` and
`--format json` to filter or consume the result. A native ID alone is not unique:
retain the Provider too. `--messages N --cut N` explicitly reads bounded deltas;
`--cut` is the total character budget per session. Coverage, Checkpoint boundary,
truncation and omitted counts accompany the result. Prefer `session-delta` for
one chosen session. `session` is an explicit native diagnostic read and is not
used by the Daily loop.

```bash
deskmate retrospective --since 2026-11-01 --format json
deskmate retrospective --since 2026-11-01 --select codex:ID --format json
deskmate retrospective --since 2026-11-01 --deepen codex:ID --max-messages 20 --format json
```

The first command reads durable evidence and native metadata, shows all candidate
Work sessions and recommends at most five. Only explicit selection reads their
bounded deltas. The user may replace the recommendation, select more than five,
or choose none. Deepening requires an explicit one-session choice and one-off
limits; it leaves configuration unchanged. Raw usage remains partitioned by
Provider, source and snapshot time. Unavailable histories limit evidence rather
than stop the day.

A Handoff uses `deskmate work-session --folder PATH` for the current card owner.
When other active work in that folder has a different Provider or ID, its resume
remains unresolved until that Work session writes a Checkpoint; routing cannot
promise to resume it. An unowned project starts new with the Default provider.

## Installation

From the cloned repository, run `./install.sh` (or `python3 -I bin/deskmate setup`).
The common setup detects compatible Claude Code and Codex CLI installations,
links the same skills into each selected Provider, migrates existing data with
backups, and verifies logging in disposable state. If both are compatible,
choose a Default provider. Existing preferences are retained.

```bash
./install.sh --non-interactive --default-provider codex
# Explicit subset; repeat --provider to select both:
./install.sh --provider claude
```

The command is linked as `~/.local/bin/deskmate`. For zsh/bash, setup adds a marked
PATH block when needed; open a new shell or follow its printed export command.
`/setup` in Claude and `$setup` in Codex use one shared setup skill. Before the
first install, Claude can discover that skill inside this repository.

Data defaults to `<repo>/data`; `DESKMATE_DATA_DIR` selects another directory.
`CLAUDE_CONFIG_DIR` selects Claude configuration/storage (default `~/.claude`);
`CODEX_HOME` selects Codex configuration/storage (default `~/.codex`). Backups and the
recoverable migration journal live under `<data>/backups/install/`. Rerunning
setup recovers an interrupted installation; if another writer changed a file,
it stops and identifies the file and preserved backups. An unresolved legacy
Project card needs `--project /absolute/project/folder` rather than a guessed path.

Setup preserves unrelated hooks and configuration. Codex hooks must also be
enabled in the installed CLI and trusted through `/hooks`; setup prints guidance.
Its synthetic logging check does not prove runtime approval. Verify actual
native delivery separately in an authorized Work session. See
[installation verification](docs/testing/installation.md).

Requires Python 3.9+ and macOS. Desktop reminders additionally need `launchctl`
and `osascript`; iTerm opens work sessions in tabs. Slack remains planned.

To remove integrations, run `deskmate remove` or `./install.sh --remove`.
Personal data, shared cards, logs and calendar files stay by default. Interactive
removal separately offers a default-no purge, requiring the exact `DELETE`.
Automation preserves data with `--non-interactive`; only an explicit
`--purge-data` deletes the selected data directory and its card links.

## Configuration

All preferences live in the selected data directory’s `config.json`, preserved by setup and applied by `install.sh`:

```json
{
  "schema_version": 1,
  "name": "Mario",
  "language": "it",
  "providers": {
    "installed": ["claude", "codex"],
    "default": "claude"
  },
  "reminders": {
    "morning": "09:00",
    "evening": "17:00",
    "days": ["mon", "tue", "wed", "thu", "fri"],
    "channels": ["mac", "calendar"]
  }
}
```

Run `bin/deskmate providers` to check which local Providers respond with a
recognizable version. Run `bin/deskmate configure` to record the compatible
Providers and choose the Default provider. With both Providers available,
non-interactive configuration requires an explicit choice, for example
`bin/deskmate configure --non-interactive --default-provider codex`.

- `name`: how the skills address you. `language`: for replies, the handoff, the lessons and the reminders (reminder texts exist in `en` and `it`, other languages fall back to English).
- `providers.installed`: compatible Providers found during configuration. `providers.default`: the Provider used when a Project card has no Work session to resume. Reminders show only the configured Providers: `/skill` for Claude Code, `$skill` for Codex CLI, with the Default provider first when both are installed. Desktop responses record that displayed Default provider without a native Work session identity.
- `channels`:
  - `mac`: an alert on the Mac that records your answer (used by `/how-did-it-go`). If the Mac is asleep at reminder time, the alert shows up on wake while it still makes sense (morning: up to 3 hours later; evening: from 1 hour before to 4 hours after); if the Mac is off, it is skipped.
  - `calendar` (not tested with a real calendar yet, see [ROADMAP.md](ROADMAP.md)): `install.sh` writes `data/deskmate-reminders.ics` with two recurring events and a notification. Open it once to import it into Apple Calendar, Google Calendar or Outlook; it reaches your phone and works with the Mac off, but records nothing. Import it again after changing times, days, language or Providers.
  - `slack`: planned, see [ROADMAP.md](ROADMAP.md).

## What gets installed

- **Command:** `~/.local/bin/deskmate` links to `bin/deskmate`.
- **Skills:** Claude links under `~/.claude/skills`; Codex links under
  `~/.agents/skills`, all pointing to the same repository `skills/` sources.
- **Hooks:** Provider adapters merge Deskmate handlers into
  `~/.claude/settings.json` and `$CODEX_HOME/hooks.json` (default `~/.codex`).
  Other handlers and preferences remain intact; repeated setup adds no duplicates.
- **Project cards:** existing Claude cards migrate to shared data with backups;
  their former locations become links to the shared cards.
- **Reminders:** the `mac` channel installs two LaunchAgents in
  `~/Library/LaunchAgents`; `calendar` generates `<data>/deskmate-reminders.ics`.
  The LaunchAgents retain the selected data directory in their environment.

## Layout

```
skills/                  the skills of the day
.claude/skills/setup/    link to the shared setup source for initial Claude discovery
bin/deskmate             stable command used by skills and automation
tools/                   internal implementations behind bin/deskmate
  adapter_claude.py       Claude native storage, hooks and launch
  adapter_codex.py        Codex native storage, hooks and launch
  work_sessions.py       routing and confirmed native ownership
  project_cards.py       shared cards, revisions and migration
  session_delta.py       bounded reads with coverage and omission counts
  retrospective.py       durable evidence, candidates and explicit selection
  hook_event.py          shared native hook handler
  activity_log.py         Provider-aware activity and atomic migration
  metrics.py             separate native Provider usage
  installation.py        recoverable setup/removal
  reminders.py           configured Provider syntax, LaunchAgents and calendar
  morning_reminder.sh    desktop wrapper through the stable command
  evening_reminder.sh    desktop wrapper through the stable command
install.sh               install, update, remove
data/                    personal files, not in git
```

## Data (`data/`, not versioned)

- `config.json`: preferences (see Configuration).
- `deskmate-reminders.ics`: calendar events, with the `calendar` channel.
- `handoff.md`: state of the sessions and things to do, rewritten every evening; the previous version goes to `archive/`.
- `lessons.md`: log of the retrospectives, with the running method experiments.
- `study-later.md`: topics to study.
- `log.csv`: one skill run or reminder per row. Columns: `date, time, weekday, event, detail, session, cwd, turns, input_tokens, cache_tokens, output_tokens, schema_version, provider`. Historical rows migrate as Claude; Provider plus native ID identifies a Work session. Raw Codex counters live separately under `usage/`. A run lasts from its command to the next `/command` of the same session, or to the end of the session: for clean numbers, run the skills in a dedicated session or finish with `/clear`.


The [Provider-neutral contract](docs/provider-neutral-cli.md) records durable
architecture and acceptance decisions. See [Daily-loop verification](docs/testing/daily-loop.md)
for synthetic evidence, native acceptance still pending, and obsolete command migration.
