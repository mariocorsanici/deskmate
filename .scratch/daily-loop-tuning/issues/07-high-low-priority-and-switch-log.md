# 07: One high and one low priority per half day, switches logged

**Status:** done (`feature/daily-loop-followups`, 2026-11-15)

"One project per half day" worked once but does not fit LLM dead times. The user prefers one high-priority and one low-priority project per half day, switching when needed.

- [x] `/whats-on-today` proposes, for the morning and the afternoon, one high- and one low-priority project.
- [x] A switch to a third project, or swapping high and low, is logged with its reason (e.g. `log_event.sh switch "<from> → <to>: <reason>"`); a one-line way to do it is documented in the skills.
- [x] `/how-did-it-go` reads the switch rows and says whether the switches were real blocks or scattering.

## Comments
- 2026-11-15 (Claude): /whats-on-today proposes a high and a low project per half day and shows the one-liner `! ~/Dev/mc_dev/deskmate/tools/log_event.sh switch "<from> → <to>: <reason>"`; /checkpoint logs a switch when the user says they are moving on; /how-did-it-go classifies each switch as a real block or scattering. `tests/test_daily_events.py` guards the logged text (it passed at once: the logger already accepted free events). The skill instructions are not yet exercised in a real session.
