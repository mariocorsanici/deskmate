# 07: One high and one low priority per half day, switches logged

**Status:** ready-for-agent (confirmed at /how-did-it-go on 2026-11-06)

"One project per half day" worked once but does not fit LLM dead times. The user prefers one high-priority and one low-priority project per half day, switching when needed.

- [ ] `/whats-on-today` proposes, for the morning and the afternoon, one high- and one low-priority project.
- [ ] A switch to a third project, or swapping high and low, is logged with its reason (e.g. `log_event.sh switch "<from> → <to>: <reason>"`); a one-line way to do it is documented in the skills.
- [ ] `/how-did-it-go` reads the switch rows and says whether the switches were real blocks or scattering.

## Comments
