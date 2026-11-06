---
name: study-later
description: Adds a topic to study later to ~/Dev/mc_dev/deskmate/data/study-later.md.
disable-model-invocation: true
argument-hint: <topic>
---

# Study later

Before working, read `~/Dev/mc_dev/deskmate/docs/agents/skill-metrics.md` and capture this invocation’s native session/start identity for the completion step.

First read `~/Dev/mc_dev/deskmate/data/config.json` and write the reason and your reply in `language`.

Append to `~/Dev/mc_dev/deskmate/data/study-later.md` one line per topic:

```markdown
- [ ] YYYY-MM-DD — **<topic>** — <why it came up: project and situation, one sentence>
```

The topic is `$ARGUMENTS`. If it is empty, suggest 1–3 topics from the current conversation and ask which ones to add. Take the "why" from the current conversation; if there is no context, ask for it in one short question.

Confirm with the added line and the number of open items.


## Complete the measurement

After completing the steps above, log this skill's end using the identity captured at its start:

```bash
~/Dev/mc_dev/deskmate/tools/log_event.sh study-later-end "" "<session-id>" "<starting-folder>"
```

Follow the completion/unfinished-run rules in `docs/agents/skill-metrics.md`; send the prepared final reply after this last tool action.
