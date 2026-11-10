# Progressive retrospective acceptance (C11)

The read-only `deskmate retrospective --since YYYY-MM-DD` command inspects
shared Project cards, period Handoffs and Provider-aware logged activity before
conversation messages. All discovered/logged/current-card Work session identities
are visible as `Provider:ID`; recommendations contain at most five identities
with reasons. Recommendations are suggestions, never an implicit selection.

## Public command

```sh
deskmate retrospective --since 2026-11-06 --format json
deskmate retrospective --since 2026-11-06 --select claude:SESSION --select codex:SESSION --format json
deskmate retrospective --since 2026-11-06 --deepen codex:SESSION --max-messages 24 --max-characters 12000 --format json
```

Omitting selection reads no Session deltas. Repeated `--select` arguments define
the whole selection, deduplicated by Provider plus native ID; the user can choose
more than five, replace the recommendations entirely or choose none. Unknown
identities reject the entire selection before any delta is read. `--since` requires the canonical `YYYY-MM-DD` format. Deepening
accepts exactly one identity and requires at least one explicit positive limit.
It cannot be combined with selection; limit overrides leave configuration intact.

Raw usage stays partitioned by Provider. Initial metrics use native metadata and
cached snapshots rather than `metrics.report`, whose refresh scans transcripts.
`usage_source` and `usage_as_of` distinguish usage provenance from live discovery;
an old usage snapshot does not replace newer activity metadata. Missing counters
are unknown, not zero. The initial view and delta reads perform no migrations,
log writes, transfer cleanup, login repair or Project card updates.

Selected reads reuse C08: configured message/character limits, matching saved
Checkpoint boundary, early/recent context, coverage and omitted counts. Adapter
failures degrade the affected session while other selected sessions continue.
No retrospective command launches a native Provider or sends a model request.

## Recorded development evidence — 2026-11-10

- Baseline: 224/224 tests passed on Python 3.14.6.
- RED: eight of nine new public scenarios failed with missing `retrospective`
  command; the invalid-input-only scenario was already green.
- GREEN: 13/13 focused scenarios passed on Python 3.14.6 and Python 3.9.6, with
  ResourceWarnings treated as errors. They cover durable/metadata collection,
  both Provider identities, all candidates/at-most-five recommendations, explicit
  replacement and selections larger than five, selected Checkpoint deltas,
  one-off deepening, validation, unavailable history, native usage separation,
  corrupt metadata/snapshots and read-only state.
- An additional RED/GREEN regression proves an old usage snapshot cannot replace
  a newer native activity time/folder. Initial-phase reader guards fail if any
  conversation or usage-refresh reader is entered.
- Instruction application, baseline: the old skill read eight
  `PRIVATE_UNSELECTED_*` conversation markers immediately and discovered only
  Claude candidates, before user selection.
- Instruction application, revised: the same fixture listed all 11 candidates
  from both Providers, recommended five with reasons and stopped for selection
  with no private conversation markers. Choosing only `codex:same` read only
  that delta (2 messages/20 characters); one-session deepening (3/40) returned
  three messages, and the next normal selection reverted to 2/20. A Claude card
  with the same native ID did not become a Codex Checkpoint boundary.

## Independent review and fixes

One independent read-only review found no Critical issues and two Important
issues, both reproduced and fixed in one pass:

- The experiment lens still called `session-stats`, opening all eight unselected
  Claude fixture transcripts even after a Codex-only selection. It now uses
  saved measurements, durable ratings and selected deltas, discloses missing
  per-mode evidence and leaves an unsupported experiment decision pending.
  Revised instruction application exercised Codex-only and empty selections;
  neither called a global transcript reader, and configuration stayed intact.
- Malformed cached metadata (`warnings: null`) could raise TypeError and lose
  the healthy Provider's report. Validation now omits invalid cached records
  with a warning, retaining all healthy evidence. Four malformed field shapes
  were observed RED and then GREEN.

The review's Minor date finding was treated as material evidence loss: Python
3.14 accepted basic/week date spellings, while lexical filters silently dropped
logged activity. Two RED/GREEN cases now require explicit YYYY-MM-DD input.
No findings from this review were deferred.

Final verification after the fix pass: **239/239 full-suite tests** on Python
3.14.6 and **15/15 focused retrospective tests** on Python 3.9.6 passed, with
ResourceWarnings as errors and no skips. The exact full-suite command is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -Werror::ResourceWarning -m unittest discover -s tests -q
```

The destination-worktree rerun is required before the focused ticket commit;
its observed result is recorded below and in the shared delivery tracker. Authenticated native acceptance is pending under C14; synthetic
instruction application does not substitute for it.

Destination-worktree verification: 239/239 full-suite tests passed before the C11 commit.
