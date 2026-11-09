# deskmate

Claude Code skills to run your working day: open it in the morning, close it in the late afternoon, and every other day take stock of how you work. Claude acts as the colleague at the next desk who keeps track of where everything stands.

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
- `## Checks`: read-only commands, one per line as ``- <label>: `<command>` ``, that tell in a few seconds whether the status is still true. `tools/check.py` runs them for `/whats-on-today` and `/call-it-a-day`.

`paused` work waits for a decision about priorities and is still proposed every morning. `standby` work is left alone until you ask for it: `check.py` skips its checks (unless you pass `--all` or name the card), and the handoff and the morning brief name it in one line. Less noise in the handoff, no slow checks (an SSH timing out on a machine that is off), and a few thousand tokens less per project each day.

`/call-it-a-day` reads the cards instead of the transcripts; it falls back to the transcript only for sessions that worked after their last checkpoint.

Use `bin/deskmate card locate <project-folder>` to get its canonical path and metadata as JSON, and `bin/deskmate card list` to discover shared cards. `bin/deskmate card migrate <project-folder>` imports an existing Claude card, preserves an exact content-addressed backup under `data/backups/project-cards/`, and installs the Claude symlink. Repeating migration is safe; differing legacy/shared content stops for explicit resolution.

Writers submit a complete UTF-8 document with `bin/deskmate card write <project-folder> --expected-revision N --provider claude|codex --session-id ID --from FILE`. Use revision `0` for a new card. Updates lock the project, check the revision and atomically replace the document. Exit `3` returns the current card on stdout: reread, reconcile and retry. Invalid metadata or unsupported schemas return `2`. Direct manual edits remain possible for recovery, but bypass revision checks and locking: avoid concurrent manual and automated updates.

Skills call the stable `bin/deskmate` command for Checks, session summaries, statistics, logging and session launch rather than depending on the individual tools that implement them.

## Work session routing

`bin/deskmate work-session --folder /path/to/project` continues a Project with
its recorded Provider and native Work session. Claude routing requires trustworthy
native index metadata: an indexless transcript filename cannot prove folder
identity, because legacy folder encoding can collide. Without an owned Work session,
it starts with the configured Default provider. Add `--dry-run` to inspect the
decision without opening a terminal or changing state; prefix the command with
`--json` for a structured result inside the standard command envelope.

If the recorded Provider or session is unavailable, the command refuses to
silently choose a replacement (exit 4). Make a deliberate new-session choice:

```bash
bin/deskmate work-session --folder /path/to/project --new --provider codex
```

`--provider` requires `--new`; it cannot turn a resume into a Provider switch.
`--title` and `--prompt` supply optional terminal and initial-message text.
This starts a new native Work session; the context-transfer and switch preview
flow remains work for later tickets.

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
and 3 (card revision conflict). Existing low-level launch commands remain during
the ongoing skill/installer migration.

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
return exit 2. This command performs local extraction only; Provider switching
and redaction/consent belong to later tickets.

## Experiments

`data/config.json` can hold a running experiment on the way of working, which the skills remind you of every morning. Today there is one, `experiments.fresh_sessions`: is it better to resume yesterday's session (`claude --resume`) or to start a new one that picks up from the project card? On the weekdays in `new_days`, `/whats-on-today` opens a new session (`open_tab.sh --new`), on the others it resumes; `/checkpoint` asks how the restart went (1–3); `tools/session_stats.py` measures each session-day from the transcripts (context at the first answer, tokens, compactions) and `/how-did-it-go` proposes a decision once both modes have `target_days` days.

## Installation

Clone the repo into `~/Dev/mc_dev/deskmate` (the skills look for their files there), then:

```bash
cd ~/Dev/mc_dev/deskmate && claude
```

and run `/setup`: it asks your preferences, checks the prerequisites, runs `install.sh` and verifies that everything responds. Run `/setup` again whenever you want to change a preference. Without Claude: edit `data/config.json` and run `./install.sh`. To remove everything: `./install.sh --remove` (data stays).

Requires macOS with `jq` and `python3`; iTerm to open sessions in tabs.

## Configuration

All preferences live in `data/config.json`, written by `/setup` (or by hand) and applied by `install.sh`:

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

- `name`: how Claude addresses you. `language`: for Claude's replies, the handoff, the lessons and the reminders (reminder texts exist in `en` and `it`, other languages fall back to English).
- `providers.installed`: compatible Providers found during configuration. `providers.default`: the Provider used when a Project card has no Work session to resume.
- `channels`:
  - `mac`: an alert on the Mac that records your answer (used by `/how-did-it-go`). If the Mac is asleep at reminder time, the alert shows up on wake while it still makes sense (morning: up to 3 hours later; evening: from 1 hour before to 4 hours after); if the Mac is off, it is skipped.
  - `calendar` (not tested with a real calendar yet, see [ROADMAP.md](ROADMAP.md)): `install.sh` writes `data/deskmate-reminders.ics` with two recurring events and a notification. Open it once to import it into Apple Calendar, Google Calendar or Outlook; it reaches your phone and works with the Mac off, but records nothing. Import it again after changing times or days.
  - `slack`: planned, see [ROADMAP.md](ROADMAP.md).

## What gets installed

- **Skills:** links from `~/.claude/skills/<name>` to `skills/<name>`, so changes in the repo apply immediately.
- **Hooks** in `~/.claude/settings.json`:
  - `UserPromptSubmit` → `tools/hook_log.sh`: logs every skill run in `data/log.csv`;
  - `Stop` → `tools/hook_tokens.sh`: fills in the tokens used by each run (in the background).
- **Reminders:** with the `mac` channel, two LaunchAgents generated from the config in `~/Library/LaunchAgents` (`com.deskmate.morning`, `com.deskmate.evening`); with `calendar`, the `.ics` file in `data/`.

## Layout

```
skills/                  the skills of the day
.claude/skills/setup/    /setup, available when running claude inside the repo
bin/deskmate             stable command used by skills and automation
tools/
  sessions.py            summary of the Claude Code sessions in a period
  log_event.sh           appends a row to the log
  token_usage.py         computes the tokens of each run from the transcripts
  hook_log.sh            UserPromptSubmit hook
  hook_tokens.sh         Stop hook
  reminders.py           reminder texts, time windows, LaunchAgents and calendar file, from the config
  morning_reminder.sh    morning alert on the Mac
  evening_reminder.sh    evening alert on the Mac
  check.py               runs the checks listed in the project cards
  session_stats.py       data for the resume-or-new-session experiment
  open_tab.sh            opens a session in a titled iTerm tab, or brings it to the front if already running
install.sh               install, update, remove
data/                    personal files, not in git
```

## Data (`data/`, not versioned)

- `config.json`: preferences (see Configuration).
- `deskmate-reminders.ics`: calendar events, with the `calendar` channel.
- `handoff.md`: state of the sessions and things to do, rewritten every evening; the previous version goes to `archive/`.
- `lessons.md`: log of the retrospectives, with the running method experiments.
- `study-later.md`: topics to study.
- `log.csv`: one skill run or reminder per row. Columns: `date, time, weekday, event, detail, session, cwd, turns, input_tokens, cache_tokens, output_tokens`. A run lasts from its command to the next `/command` of the same session, or to the end of the session: for clean numbers, run the skills in a dedicated session or finish with `/clear`.
