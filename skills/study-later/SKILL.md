---
name: study-later
description: Adds a topic to study later to ~/Dev/mc_dev/deskmate/data/study-later.md.
disable-model-invocation: true
argument-hint: <topic>
---

# Study later

Before working, read `~/Dev/mc_dev/deskmate/docs/agents/skill-metrics.md` and capture this invocation’s native session/start identity for the completion step.

First read `~/Dev/mc_dev/deskmate/data/config.json` and write the reason and your reply in `language`.

Add to `~/Dev/mc_dev/deskmate/data/study-later.md` one line per topic:

```markdown
- [ ] YYYY-MM-DD — P<1|2|3> — **<topic>** — <why it came up: project and situation, one sentence>
```

The topic is `$ARGUMENTS`. If it is empty, suggest 1–3 topics from the current conversation and ask which ones to add. Take the "why" from the current conversation; if there is no context, ask for it in one short question.

**Priority.** Propose one, with a short reason, and let the user confirm or change it in the same question as any other you need to ask:
- **P1:** needed for the primary work project.
- **P2:** needed for the secondary project or a project in progress.
- **P3:** useful, no urgency.

Read the current priorities from the home memory (`current-priorities`) and the project cards. If the user gives a priority with the topic, use it without asking.

The list stays sorted by priority: insert the line after the last open item with the same priority (P1 before P2 before P3), not at the end of the file. Do not reorder or rewrite the other lines. A line without a priority, from before this format, is P3 until the user says otherwise.

Confirm with the added line, its position and the number of open items per priority.


## Complete the measurement

After completing the steps above, log this skill's end using the identity captured at its start:

```bash
~/Dev/mc_dev/deskmate/tools/log_event.sh study-later-end "" "<session-id>" "<starting-folder>"
```

Follow the completion/unfinished-run rules in `docs/agents/skill-metrics.md`; send the prepared final reply after this last tool action.
