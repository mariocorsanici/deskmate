# 07: One high and one low priority per half day, switches logged

**Status:** needs-triage (experiment, confirm at the next /how-did-it-go)

"One project per half day" worked once but does not fit LLM dead times. The user prefers one high-priority and one low-priority project per half day, switching when needed.

- [ ] `/whats-on-today` proposes, for the morning and the afternoon, one high- and one low-priority project.
- [ ] A switch to a third project, or swapping high and low, is logged with its reason (e.g. `log_event.sh switch "<from> → <to>: <reason>"`); a one-line way to do it is documented in the skills.
- [ ] `/how-did-it-go` reads the switch rows and says whether the switches were real blocks or scattering.

## Comments
