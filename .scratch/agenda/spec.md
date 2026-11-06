# Agenda: non-development days and tasks

Status: ready-for-agent

## Problem Statement

Deskmate only knows development work: project cards in repos, Claude sessions, git checks. Travel days, office work and non-code documentation are invisible to it. On 2026-11-05 the user was travelling; on 2026-11-06 `/whats-on-today` treated that day as a missed `/call-it-a-day` and the handoff as current. Non-code tasks (a trip report, an expense note, a document to review) have no place to live, and the morning plan assumes the whole day is free for code.

## Goals (from the user, 2026-11-06)

1. Do not lose non-development tasks: they stay in front of the user until closed.
2. Non-development days (travel, office) are not missed steps and do not count as development days.
3. The morning plan accounts for days or half days already taken.

Not a goal: time tracking. No hours, no mandatory dates. Dates are references, never constraints.

## Solution

One file `data/agenda.md`, written only through `tools/agenda.py`, and a new skill `/agenda` that makes it deterministic where a datum goes: anything after `/agenda` lands in the agenda, never in the handoff, the cards or `study-later.md`. The other skills read and write the agenda only through `tools/agenda.py`.

### File format

Keywords follow `config.json` `language` (`it` and `en` supported; table below). Example in Italian:

```markdown
# Agenda

Giorni e attività non di sviluppo. Le date sono un riferimento, non un vincolo.

## Giorni
- 2026-11-12 · giornata · trasferta Monfalcone
- 2026-11-14 · pomeriggio · ufficio

## Attività
- [ ] Report trasferta Monfalcone · quando: 2026-11-13 · entro: 2026-11-20
- [ ] Nota spese novembre · entro: 2026-11-30
- [ ] Rivedere documento offerta X
- [x] Rinnovo badge · fatto 2026-11-06
```

| meaning | it | en |
|---|---|---|
| days section | `## Giorni` | `## Days` |
| tasks section | `## Attività` | `## Tasks` |
| whole day / morning / afternoon | `giornata` / `mattina` / `pomeriggio` | `day` / `morning` / `afternoon` |
| planned date | `quando:` | `when:` |
| deadline | `entro:` | `due:` |
| closed on | `fatto` | `done` |

- **Day line:** `- YYYY-MM-DD · <part> · <description>`.
- **Task line:** `- [ ] <description>` optionally followed by ` · <when>: YYYY-MM-DD` and/or ` · <due>: YYYY-MM-DD`, in that order; closed: `- [x] <description> · <done> YYYY-MM-DD` (dates kept if present).
- One agenda for everything; tasks are not linked to project cards (the description can name a project).

### Deterministic handling of a missing or hand-damaged file

The user may edit the file by hand. `tools/agenda.py` behaves exactly as follows, and tests cover each rule:

- **Missing file:** any command creates it with the header and both sections empty, and prints one line saying so.
- **Invalid line** (inside `Giorni`/`Attività`, not matching the format): never modified, moved or deleted, kept byte for byte. Every command prints, for each one, `agenda.md:<line>: non valida: <text>` (`invalid` in English). Writes proceed on the valid lines; archiving skips invalid lines.
- **Exit code:** `0` when the file is clean, `2` when it has invalid lines (after doing the work), `1` on a usage error (nothing written). Skills always report the invalid lines to the user.
- **Text outside the two sections** (title, notes): preserved verbatim and ignored.
- **Missing section:** recreated empty at the end of the file, and reported.
- **Concurrent writes:** an exclusive lock, as for `log.csv` (`data/.agenda.lock`).
- Writes rewrite only the touched line or append to the section; every other byte stays as it was.

### `tools/agenda.py` commands

- `add "<description>" [--when YYYY-MM-DD] [--due YYYY-MM-DD]`
- `day YYYY-MM-DD <day|morning|afternoon> "<description>"` (part given in English on the command line, written in `language`); a day already present with an overlapping part is replaced and the replacement reported.
- `done "<text>"`: closes the open task whose description contains `<text>` (case- and accent-insensitive). Zero matches: exit 1, nothing written. More than one: exit 1, prints the candidates, nothing written.
- `remove "<text>"`: same matching, deletes a task or day line (for mistakes).
- `list [--today YYYY-MM-DD]`: machine-readable sections (default today):
  - `today:` the day entry for today, if any;
  - `due:` open tasks with `when` ≤ today;
  - `deadline:` open tasks with `due` within the next 3 working days or past;
  - `undated:` count of open tasks without dates;
  - `upcoming:` day entries in the next 5 working days;
  - `closed:` tasks closed since a given date (`--closed-since YYYY-MM-DD`).
- `is-dev-day YYYY-MM-DD`: exit 3 if the agenda has a whole-day (`day`/`giornata`) entry for that date; otherwise exit 2 if the file has invalid lines, else 0. Exit 3 wins over 2 (invalid lines are still printed). Half days (`morning`/`afternoon`) count as development days. Used by other skills to exclude non-development days.
- `archive [--today YYYY-MM-DD] [--closed-before YYYY-MM-DD]`: moves past day entries, and closed tasks closed before the given date, to `data/archive/agenda-YYYY-MM.md`.

`--today` exists so tests are independent of the clock.

### The `/agenda` skill

Like `/study-later`: `disable-model-invocation: true`, argument hint `<what>`, replies in `language`.

- `/agenda <text>`: the skill reads the sentence and decides only *what kind* of entry it is (day, task, close) and the absolute dates; then it calls `tools/agenda.py`. Relative dates resolve forward: "giovedì" is the next Thursday, never a past one; "il 13" is the next 13th. If the sentence is ambiguous (e.g. "venerdì" said on a Friday, or "fatto" matching several tasks), it asks instead of guessing.
- `/agenda` alone: shows the agenda (`list`) in a short block.
- It answers with the line exactly as written, plus one-line notes: `due` before `when`, a weekend day, a replaced day entry, invalid lines.
- `tools/hook_log.sh` logs `agenda` like the other skills.

### Changes to the other skills

- **`/whats-on-today`:**
  - If today is a whole non-development day: say so first, show only the agenda block, do not run project checks or open sessions unless the user asks.
  - If today is a half day: the development plan covers only the other half.
  - A "Non sviluppo" block before the suggested order: `due`, `deadline` (highlighted), `undated` as one count line, `upcoming` days in one line.
  - Missed steps: dates where `is-dev-day` exits 3 are skipped. The handoff is still declared stale across them (ticket 03 of `daily-loop-tuning`).
- **`/call-it-a-day`:** one question in one line: "Qualcosa di non sviluppo da segnare o chiudere?"; whatever the user says is written through `tools/agenda.py`. Runs `archive` for past days. If tomorrow is a non-development day, one line in the handoff ("Domani trasferta: niente sessioni").
- **`/how-did-it-go`:** tasks closed since the last retrospective in one line (`list --closed-since`), then `archive --closed-before <today>`.
- README and `install.sh`: the new skill and the file, `data/agenda.md` never overwritten.

## Branching and dependencies

- Branch `feature/agenda`, from `develop` at `70468e3`. Independent from `feature/daily-loop-tuning`: neither waits for the other.
- Ticket 06 links the two: once both are on `develop`, the stale handoff (03) and the development-day count (05) of `daily-loop-tuning` use `is-dev-day`.
- `feature/codex-cli-support` rewrites the skills and moves project cards: merge after it, rebasing first, as for `daily-loop-tuning`. Keep the agenda under `data/`, which that branch keeps as the data root.

## Manual validation phrases (for the skill, not unit tests)

Run on a known date and check the written line:
- `/agenda giovedì trasferta Monfalcone` → day line for the next Thursday, `giornata`.
- `/agenda venerdì pomeriggio ufficio` → `pomeriggio`.
- `/agenda report Monfalcone entro il 20, lo faccio il 13` → task with `quando` the 13th and `entro` the 20th.
- `/agenda nota spese novembre` → undated task.
- `/agenda fatto report` with two "report" tasks → the skill asks which.
- `/agenda` → the list.
The user can ask for more phrases by hand during validation.

## Out of scope

Hours, time tracking, calendar integration, Slack, reminders tied to agenda dates.
