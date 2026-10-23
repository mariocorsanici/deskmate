# deskmate

Claude Code skills to run your working day: open it in the morning, close it around 17:00, and every other day take stock of how you work. Claude acts as the colleague at the next desk who keeps track of where everything stands.

## A typical day

| When | Skill | What it does |
|---|---|---|
| 9:00 (reminder) | `/whats-on-today` | rereads the handoff, checks what changed, flags skipped steps, suggests the order of the day and opens the sessions in iTerm |
| during the day | `/study-later <topic>` | notes a topic to study later |
| Mon, Wed, Fri before closing | `/how-did-it-go` | retrospective on organisation and method, updates `data/lessons.md` |
| 17:00 (reminder) | `/call-it-a-day` | snapshots the open sessions and writes `data/handoff.md` for tomorrow |

After closing: study the topics you set aside, or admin work.

## Installation

Clone the repo into `~/Dev/deskmate` (the skills look for their files there), then:

```bash
cd ~/Dev/deskmate && claude
```

and run `/setup`: it asks your name and language, checks the prerequisites, runs `install.sh` and verifies that everything responds. Without Claude: `./install.sh --name <name> --language <en|it>`. To remove everything: `./install.sh --remove` (data stays).

Requires macOS with `jq` and `python3`; iTerm to open sessions in tabs.

## Name and language

`data/config.json` holds `name` (how Claude addresses you) and `language` (for Claude's replies, the handoff, the lessons and the reminders). The skills are written in English and answer in your language; the reminders support `en` and `it` and fall back to English. Change them by running `install.sh` again with `--name` / `--language`.

## What gets installed

- **Skills:** links from `~/.claude/skills/<name>` to `skills/<name>`, so changes in the repo apply immediately.
- **Hooks** in `~/.claude/settings.json`:
  - `UserPromptSubmit` → `tools/hook_log.sh`: logs every skill run in `data/log.csv`;
  - `Stop` → `tools/hook_tokens.sh`: fills in the tokens used by each run (in the background).
- **Reminders** (`launchd/`, installed in `~/Library/LaunchAgents`): 9:00 and 17:00, Monday to Friday. If the Mac is asleep at reminder time, the alert shows up on wake while it is still in its window (morning until 12:00, evening 16:00–21:00); if the Mac is off, the alert is skipped.

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
  morning_reminder.sh    9:00 alert
  evening_reminder.sh    17:00 alert
launchd/                 LaunchAgent templates (__ROOT__ = repo path)
install.sh               install, update, remove
data/                    personal files, not in git
```

## Data (`data/`, not versioned)

- `config.json`: name and language.
- `handoff.md`: state of the sessions and things to do, rewritten every evening; the previous version goes to `archive/`.
- `lessons.md`: log of the retrospectives, with the running method experiments.
- `study-later.md`: topics to study.
- `log.csv`: one skill run or reminder per row. Columns: `date, time, weekday, event, detail, session, cwd, turns, input_tokens, cache_tokens, output_tokens`. A run lasts from its command to the next `/command` of the same session, or to the end of the session: for clean numbers, run the skills in a dedicated session or finish with `/clear`.
