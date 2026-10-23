---
name: study-later
description: Adds a topic to study later to ~/Dev/deskmate/data/study-later.md.
disable-model-invocation: true
argument-hint: <topic>
---

# Study later

First read `~/Dev/deskmate/data/config.json` and write the reason and your reply in `language`.

Append to `~/Dev/deskmate/data/study-later.md` one line per topic:

```markdown
- [ ] YYYY-MM-DD — **<topic>** — <why it came up: project and situation, one sentence>
```

The topic is `$ARGUMENTS`. If it is empty, suggest 1–3 topics from the current conversation and ask which ones to add. Take the "why" from the current conversation; if there is no context, ask for it in one short question.

Confirm with the added line and the number of open items.
