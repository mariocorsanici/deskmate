---
name: study-later
description: Adds a topic to the study list in the selected Deskmate data directory.
disable-model-invocation: true
argument-hint: <topic>
---

# Study later

Use the same skill in either Provider: `/study-later` in Claude Code, `$study-later` in Codex CLI. References to other skills use that same native prefix. Resolve `<data>` from `DESKMATE_DATA_DIR` (expand `~` and resolve relative paths from the invocation directory), otherwise `<repo>/data`. Resolve `<repo>` from the real target of the installed `deskmate` command (its parent is `bin/`), or use the current repository before installation. Read and write all personal files under that root. Use the installed `deskmate` command; before installation, use the repository’s `bin/deskmate`.

First read `<data>/config.json` and write the reason and your reply in `language`.

Append to `<data>/study-later.md` one line per topic:

```markdown
- [ ] YYYY-MM-DD — **<topic>** — <why it came up: project and situation, one sentence>
```

The topic is the text following the native skill name: Claude supplies `$ARGUMENTS`; in Codex use the arguments from the invoking user message. If it is empty, suggest 1–3 topics from the current conversation and ask which ones to add. Take the "why" from the current conversation; if there is no context, ask for it in one short question.

Confirm with the added line and the number of open items.
