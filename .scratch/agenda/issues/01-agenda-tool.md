# 01: tools/agenda.py and its tests

**Status:** ready-for-agent

Implement `tools/agenda.py` as in the spec ("File format", "Deterministic handling", "commands"), Python standard library only, run with `python3 -I`.

- [ ] Commands `add`, `day`, `done`, `remove`, `list`, `is-dev-day`, `archive`, with `--today` for clock-independent tests.
- [ ] Keywords in `it` and `en` from `config.json` `language`.
- [ ] Missing file created; invalid lines kept byte for byte and reported as `agenda.md:<line>: ...`; exit codes 0 / 1 / 2 / 3 exactly as in the spec; missing section recreated; text outside sections preserved.
- [ ] Exclusive lock on writes.
- [ ] `tests/test_agenda.py` covers every bullet above, plus: overlapping day parts, `done` with zero and with two matches, `list` buckets on a fixed date, archive to `data/archive/agenda-YYYY-MM.md`, a write that leaves all other bytes unchanged.

## Comments
