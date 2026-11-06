# 01: tools/agenda.py and its tests

**Status:** implemented

Implement `tools/agenda.py` as in the spec ("File format", "Deterministic handling", "commands"), Python standard library only, run with `python3 -I`.

- [x] Commands `add`, `day`, `done`, `remove`, `list`, `is-dev-day`, `archive`, with `--today` for clock-independent tests.
- [x] Keywords in `it` and `en` from `config.json` `language`.
- [x] Missing file created; invalid lines kept byte for byte and reported as `agenda.md:<line>: ...`; exit codes 0 / 1 / 2 / 3 exactly as in the spec; missing section recreated; text outside sections preserved.
- [x] Exclusive lock on writes.
- [x] `tests/test_agenda.py` covers every bullet above, plus: overlapping day parts, `done` with zero and with two matches, `list` buckets on a fixed date, archive to `data/archive/agenda-YYYY-MM.md`, a write that leaves all other bytes unchanged.

## Comments

2026-11-06: Implemented the seven commands. `list` stdout is JSON; notices and invalid-line diagnostics are stderr. Existing English and Italian entries remain readable after a config-language change. `done --today` supplies a deterministic completion date. `is-dev-day` consults monthly archives so historical non-development days remain excluded after evening cleanup.

Verification: `python3 -I -B -m unittest discover -s tests -v` — 35 tests pass, including 20 concurrent initial additions, lock blocking, exact CRLF/binary preservation and archive boundaries. The same suite was observed failing before the CLI existed. No installed personal data was accessed.
