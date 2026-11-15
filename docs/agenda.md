# Agenda reference

`data/agenda.md` holds non-development days and tasks, independently of project
cards. Dates are references, not constraints; tasks stay open until explicitly
completed. Use `python3 -I ~/Dev/mc_dev/deskmate/tools/agenda.py --help` for
commands, and each command's `--help` for arguments. All edits, including
archiving, go through this tool. The data file is personal and unversioned.

## Interpreting natural language

Get today's local date first. Classify an explicit day/half day as a day entry,
an action to do as a task, and an explicit completion as `done`. The CLI takes
absolute ISO dates; resolving relative dates is the skill's responsibility.

- A named weekday means its next future occurrence. When the weekday is today
  and the user has not said today or next week, ask which one.
- A day number such as "il 13" means the next such calendar date. Advance to
  the next month containing that day if needed; a nonexistent date is never
  silently rolled into another date. If today has that number and the intent
  is unclear, ask. Explicit "oggi"/"today" means today.
- A dated trip or office day reserves the whole day by default; explicit
  morning or afternoon reserves that half only. For tasks, "quando/when"
  records the planned date and "entro/due" the deadline. Keep both if given.
- Resolve an ambiguous date or intent with one question before any agenda
  command. For an ambiguous task completion/removal, call `done`/`remove`:
  the tool prints candidates and leaves the agenda unchanged on exit 1.

Descriptions must be non-empty single lines. The separator ` · ` is reserved
for structured fields: if it appears in a supplied description, propose plain
wording and confirm the intended text. Pass text as a safely quoted argument,
never as shell code.

## Output and diagnostics

`list` prints one JSON object on stdout; every entry is its original Markdown
line, without its newline:

| Key | Value |
| --- | --- |
| `today` | day entries for `--today` (default local today) |
| `due` | open tasks planned on or before today |
| `deadline` | open tasks whose deadline is past or within the next 3 working days |
| `undated` | number of open tasks with neither planned date nor deadline |
| `upcoming` | day entries after today through the next 5 working days |
| `closed` | completed tasks from `--closed-since`, inclusive, through today; empty without that option |

Working days for these windows are Monday–Friday, without a holiday calendar.
The third/fifth following weekday is the inclusive end date; weekend dates
inside the interval remain visible. A task may appear in both `due` and
`deadline`: show it once with its deadline highlighted.

Mutating commands print the affected entry lines. Initialization, repaired
sections, replacements, date warnings and invalid-line diagnostics are stderr.
Report those diagnostics even when stdout contains valid results.

| Exit | Meaning |
| --- | --- |
| 0 | success, clean file |
| 1 | usage or command failure; a usage/matching error leaves agenda content unchanged |
| 2 | operation completed; invalid lines were preserved and reported |
| 3 | `is-dev-day` found a whole non-development day; also report any invalid-line diagnostics |

Exit 2 is successful work with warnings: repeating a write would duplicate it.
For `is-dev-day`, 3 takes precedence over 2. Half-day entries count as
development days, including two separate half-day entries. An unlisted date
returns 0, including weekends; daily-loop weekend handling is separate.

## Archive and integration

`archive` moves days before today into `data/archive/agenda-YYYY-MM.md`.
Completed tasks move only when `--closed-before` is supplied, and only when
their completion date is strictly before that cutoff. Their completion month
selects the archive. `done --today` makes completion-date tests deterministic.
`is-dev-day` also consults that date's monthly archive, so past travel days
remain recognizable after evening cleanup. Reads and writes use the same
exclusive `data/.agenda.lock`.

Collect `list --closed-since` results before retrospective archiving. The
separate daily-loop tuning follow-up connects historical non-development days
to stale-handoff wording and the two-development-day retrospective cadence.
