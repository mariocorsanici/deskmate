---
name: how-did-it-go
description: Retrospective on organisation and method over the last few days; updates lessons.md.
disable-model-invocation: true
---

# How did it go

A **retrospective** on *how* the work went over the last few days, not on its technical content: organisation, method, use of Claude. It runs on Monday, Wednesday and Friday, before `/call-it-a-day`. Data files live in `~/Dev/mc_dev/deskmate/data/`. First read `~/Dev/mc_dev/deskmate/data/config.json`: address the user by `name`, and write every reply and the `lessons.md` entry in `language`.

## Steps

1. **Period.** From the day after the latest entry in `~/Dev/mc_dev/deskmate/data/lessons.md` until today; if `lessons.md` has no entries yet, the last 3 days.

2. **Collect.** Run `python3 -I ~/Dev/mc_dev/deskmate/tools/sessions.py --since <start> --messages 60 --cut 400` and read the handoffs of the period in `~/Dev/mc_dev/deskmate/data/archive/` and `handoff.md`: they are the plan, the transcripts are what happened. `~/Dev/mc_dev/deskmate/data/log.csv` tells when the skills ran, how the user answered the reminders and how many tokens each run used.

3. **Analyse** through these lenses. Every observation cites its evidence: session, time, what happened.
   - **Rhythm:** from the log, days without opening or closing, skipped retrospectives, reminders snoozed or ignored.
   - **Plan and reality:** what was in the handoff and got done, postponed, forgotten.
   - **Rework:** false starts, retracted answers, stale notes taken at face value, work done twice.
   - **Waiting and blockers:** time stuck waiting for people, permissions, access.
   - **Context switches:** parallel sessions, interruptions, work resumed several times.
   - **Use of Claude:** vague requests that needed clarification, things Claude could have done alone or that were better done by hand.
   - **What worked:** to repeat.
   Done when every lens has at least one observation with evidence, or a line saying "nothing to report".

4. **Previous experiments.** For each experiment in the latest entry: did it happen? Did it help? Decide whether to keep, change or drop it. Compare with older entries too: a problem seen two or more times is **recurring**.

5. **Talk it through.** Present the 3–5 strongest observations, recurring ones first, and ask for the user's reading: it is a conversation, and their view counts more than the transcripts. Agree on 1–3 experiments for the next days, concrete and checkable ("one session per project", not "be tidier").

6. **Record.** Append to `lessons.md`, with the labels translated into `language`:

   ```markdown
   ## <YYYY-MM-DD> (period <start> → <end>)
   **What worked:** …
   **To improve:** … (mark *recurring* where it applies)
   **Previous experiments:** <name> → kept / changed / dropped, why
   **Running experiments:**
   - …
   ```

   Then remind the user that `/call-it-a-day` is the next step.
