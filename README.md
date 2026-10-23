# deskmate

Claude Code skills to run your working day: open it in the morning, close it in the late afternoon, and every other day take stock of how you work. Claude acts as the colleague at the next desk who keeps track of where everything stands.

## A typical day

| When | Skill | What it does |
|---|---|---|
| morning (reminder) | `/whats-on-today` | rereads the handoff, checks what changed, flags skipped steps, suggests the order of the day and opens the sessions in iTerm |
| during the day | `/study-later <topic>` | notes a topic to study later |
| Mon, Wed, Fri before closing | `/how-did-it-go` | retrospective on organisation and method, updates `data/lessons.md` |
| evening (reminder) | `/call-it-a-day` | snapshots the open sessions and writes `data/handoff.md` for tomorrow |

After closing: study the topics you set aside, or admin work.

## Installation

Clone the repo into `~/Dev/deskmate` (the skills look for their files there), then:

```bash
cd ~/Dev/deskmate && claude
```

and run `/setup`: it asks your preferences, checks the prerequisites, runs `install.sh` and verifies that everything responds. Run `/setup` again whenever you want to change a preference. Without Claude: edit `data/config.json` and run `./install.sh`. To remove everything: `./install.sh --remove` (data stays).

Requires macOS with `jq` and `python3`; iTerm to open sessions in tabs.

## Configuration

All preferences live in `data/config.json`, written by `/setup` (or by hand) and applied by `install.sh`:

```json
{
  "name": "Mario",
  "language": "it",
  "reminders": {
    "morning": "09:00",
    "evening": "17:00",
    "days": ["mon", "tue", "wed", "thu", "fri"],
    "channels": ["mac", "calendar"]
  }
}
```

- `name`: how Claude addresses you. `language`: for Claude's replies, the handoff, the lessons and the reminders (reminder texts exist in `en` and `it`, other languages fall back to English).
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
tools/
  sessions.py            summary of the Claude Code sessions in a period
  log_event.sh           appends a row to the log
  token_usage.py         computes the tokens of each run from the transcripts
  hook_log.sh            UserPromptSubmit hook
  hook_tokens.sh         Stop hook
  reminders.py           reminder texts, time windows, LaunchAgents and calendar file, from the config
  morning_reminder.sh    morning alert on the Mac
  evening_reminder.sh    evening alert on the Mac
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
