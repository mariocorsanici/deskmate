# 02: The /agenda skill

**Status:** done (merged into develop as `1420b75`, 2026-11-15)
**Blocked by:** 01

- [x] `skills/agenda/SKILL.md` as in the spec ("The `/agenda` skill"), modelled on `study-later`.
- [x] It only classifies the sentence and resolves dates; all reads and writes go through `tools/agenda.py`.
- [x] Ambiguous dates or multiple matches → one question, nothing written.
- [x] Reply: the written line, plus the one-line notes, plus any invalid lines reported by the tool.
- [x] `tools/hook_log.sh` logs `agenda`; `install.sh` installs the skill; README updated.
- [x] Manual validation with the phrases in the spec, recorded in this ticket's Comments.

## Comments

2026-11-06: Added the user-invoked skill and shared reference `docs/agenda.md`, logging allowlist, README entries and installer initialization through the CLI only when agenda.md is absent. Full suite: 39 tests pass; shell syntax checks pass. Both new hook paths were observed failing before the allowlist change.

An independent agent first applied the old skill instructions: none routed `/agenda`; morning always continued to project checks; evening had no durable non-code task store; retrospective read no agenda completions. After the new skill/reference, the agent resolved and executed all spec phrases against an Italian-configured temporary CLI copy on Friday 2026-11-06:
- Thursday travel -> `day 2026-11-12 day ...`, exact Italian line verified.
- Friday afternoon -> asked today vs next Friday, no CLI call or byte change.
- Report planned 13/deadline 20 -> exact `quando: 2026-11-13` and `entro: 2026-11-20`.
- November expense note -> undated task, no invented date.
- Done report with two candidates -> exit 1, both candidates, byte-identical agenda.
- No arguments -> parsed JSON, correct upcoming travel and undated count, no byte changes.
This validates tool execution and agent interpretation; a live installed skill invocation remains a user acceptance check.

The real install.sh Data block was also executed in a temporary root: Italian initialization passed; repeated setup preserved bytes; an existing damaged agenda with missing sections and a non-UTF-8 byte remained byte-identical. No global installation, hooks or reminders were changed.
