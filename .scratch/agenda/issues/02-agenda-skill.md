# 02: The /agenda skill

**Status:** ready-for-agent
**Blocked by:** 01

- [ ] `skills/agenda/SKILL.md` as in the spec ("The `/agenda` skill"), modelled on `study-later`.
- [ ] It only classifies the sentence and resolves dates; all reads and writes go through `tools/agenda.py`.
- [ ] Ambiguous dates or multiple matches → one question, nothing written.
- [ ] Reply: the written line, plus the one-line notes, plus any invalid lines reported by the tool.
- [ ] `tools/hook_log.sh` logs `agenda`; `install.sh` installs the skill; README updated.
- [ ] Manual validation with the phrases in the spec, recorded in this ticket's Comments.

## Comments
