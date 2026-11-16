---
name: agenda
description: Records non-development days and tasks, or shows the agenda.
disable-model-invocation: true
argument-hint: <what>
---

# Agenda

Use the same skill in either Provider: `/agenda` in Claude Code, `$agenda` in Codex CLI. References to other skills use that same native prefix. Resolve `<data>` from `DESKMATE_DATA_DIR` (expand `~` and resolve relative paths from the invocation directory), otherwise `<repo>/data`. Resolve `<repo>` from the real target of the installed `deskmate` command (its parent is `bin/`), or use the current repository before installation. Read and write all personal files under that root. Use the installed `deskmate` command; before installation, use the repository’s `bin/deskmate`.

Before working, read `<repo>/docs/agents/skill-metrics.md` and capture this invocation’s Provider, native session ID and starting folder for the completion step.

Keep non-development days and tasks in the agenda until they are completed. First read `<data>/config.json`; reply in `language`. Read `<repo>/docs/agenda.md` for date interpretation, output and exit codes. Get today's local date before resolving relative dates.

1. **Interpret the request.** The request is the text following the native skill name: Claude supplies `$ARGUMENTS`; in Codex use the arguments from the invoking user message. Decide whether the user is reserving a day/half day, adding a task, closing a task or explicitly removing a mistaken entry. Resolve all dates to `YYYY-MM-DD` using the reference. If a date or intent is ambiguous, ask one short question before running any agenda command.

2. **Run the tool.** All agenda reads and writes use `deskmate agenda`. Pass each description as one safely quoted argument. Agenda input belongs only in the agenda; project cards, handoff and study-later are separate stores.
   - No arguments: `list`; render the returned JSON in a short block in `language`, with deadline tasks highlighted and undated tasks as a count.
   - Non-development day: `day <date> <day|morning|afternoon> "<description>"`. Use `day` for a whole day when no half is specified.
   - Task: `add "<description>"`, with `--when` and/or `--due` only when supplied. A task needs no date.
   - Completion: `done "<description fragment>"`. Let the tool resolve the match. On exit 1 with multiple candidates, show them and ask which one; on no match, ask what the user intended. Both leave agenda content unchanged.
   - Explicit correction/removal: `remove "<description fragment>"`, with the same ambiguity handling. Completing a task uses `done` so its history remains available.

3. **Confirm.** For a successful write, quote the exact entry line from stdout. For a removal, identify that line as removed. Report date-order warnings, weekend dates, replacements, initialization/section repair and every invalid-line diagnostic in short notes. Exit 2 means the change succeeded alongside invalid lines: report them without repeating the write. A usage error means no agenda change; resolve it before retrying.


## Complete the measurement

After completing the steps above, log this skill's end using the identity captured at its start:

```bash
deskmate log-event agenda-end "" "<session-id>" "<starting-folder>" --provider <claude|codex>
```

Follow the completion/unfinished-run rules in `<repo>/docs/agents/skill-metrics.md`; send the prepared final reply after this last tool action. While waiting for the user's answer to an ambiguity question, the skill is still open.
