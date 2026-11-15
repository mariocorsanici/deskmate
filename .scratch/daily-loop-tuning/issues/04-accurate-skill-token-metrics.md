# 04: Measure skill runs up to their end, not to the next command

**Status:** ready-for-agent

**Implementation:** complete (automated/local verification; native acceptance not claimed).

`tools/token_usage.py` counts a run from its command to the next `/command` of the same session or the session's end. Work done after the skill inflates it (2026-11-03 `/checkpoint` in vlm: 182 turns, 96M tokens; 2026-11-06 `/whats-on-today`: 28 turns including a recap and a code change). Durations of the skills themselves cannot be compared over time.

- [x] Each deskmate skill logs an end event as its last step (e.g. `log_event.sh <skill>-end "" <session> <cwd>`), or an equivalent marker `token_usage.py` can find in the transcript.
- [x] `token_usage.py` closes a run at the first of: its end marker, the next command, the session end. Old rows without a marker keep today's behaviour.
- [x] The log keeps the old figure distinguishable (e.g. a column or event name), so earlier rows are not silently mixed with the new measure.
- [x] Tests cover: run with end marker followed by unrelated work; run without marker; two skills in a row.
- [x] `/how-did-it-go` uses only end-marked runs when it talks about the cost of the skills.

## Comments

Implemented 2026-11-06. All five skills capture start identity and explicitly finish successful runs. Precise session/folder-matched end events bound usage, legacy windows stay labeled and retrospectives filter bounded samples. Synthetic usage/CSV regressions passed after observed failures; shared locking and atomic writes preserve history and extension columns. See `docs/testing/daily-loop-tuning.md`; authenticated native behavior remains untested.
