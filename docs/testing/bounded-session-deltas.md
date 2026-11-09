# Bounded Session delta verification

Verified 2026-11-09 for provider-neutral CLI ticket 08.

## Automated evidence

- Baseline: 132 tests passed at `60b87d0`, with ResourceWarnings as errors.
- Initial public-command tests ran RED against the missing `session-delta` command.
- Focused suite: 25 tests pass with both the current Python and macOS system Python.
- Final full suite: **157 tests pass**, no failures/skips, ResourceWarnings as errors.
- `git diff --check`: passes.

Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -Werror::ResourceWarning -m unittest discover -s tests -q
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -Werror::ResourceWarning -m unittest tests.test_session_delta -q
git diff --check
```

Public CLI fixtures use isolated HOME, CODEX_HOME and DESKMATE_DATA_DIR. They
exercise actual Claude JSONL, Codex rollout JSONL and paginated SQLite readers,
shared Project card writes, configuration and one-command overrides, exact
default limits, early/recent selection, Unicode budgets, counts and coverage,
cancelled Checkpoint invocation, Provider/session mismatch, corrupt history,
metadata/tool exclusions and text/JSON output. Streaming-consumer checks confirm
messages are delivered without constructing the full conversation list.

No installed personal data, authenticated model requests or Provider launches
were used. Native acceptance remains ticket 14.

## Independent review and corrections

One independent read-only review found four Important issues and no Critical
issues. The five additional public regression tests first failed in ten subcases,
then passed after the corrections:

1. `test_late_claude_folder_metadata_still_resolves_saved_checkpoint`: when
   native metadata establishes the project late, replay extraction as a second
   bounded streaming pass against the resolved Checkpoint; early candidates and
   counts cannot retain already-saved context.
2. `test_escaped_unicode_surrogates_degrade_safely_in_all_stores_and_formats`:
   reject malformed Unicode before retention and disclose missing coverage in
   both JSON and text results.
3. `test_naive_native_timestamps_are_utc_even_with_local_checkpoint_timezone`
   and `test_invalid_native_timestamps_disclose_partial_coverage_without_checkpoint`:
   match both adapters' UTC convention for naive native times and validate all
   message timestamps, including when no Checkpoint exists. Unknown times remain
   useful but visibly unknown from session start; they are excluded after a
   known boundary. Representability errors become structured validation errors.
4. `test_malformed_conversation_content_is_not_reported_as_complete_empty_delta`:
   native adapters now disclose malformed conversation content in delta mode;
   valid tool/reasoning exclusions and existing full-session/usage behavior stay
   intact.

The review's Minor extreme-date conversion overflow was also resolved by the
shared timestamp representability validation required for correction 3. No
deferred Minor findings remain. No second review was needed: the public RED/GREEN
regressions and final full suite verify the corrections.

## Scope decisions

- The existing ready ticket and explicit implementation request authorize inline
  execution. The work stays on the existing feature branch; no push or merge.
- A matching durable Project card supplies the automatic boundary. A native
  checkpoint prompt alone may have been cancelled. Legacy card times assume local
  time and disclose minute precision; without matching saved state, coverage
  explicitly starts at session start. This can include already-recorded history
  when no matching durable boundary remains, within the same limits.
- Native runtime acceptance is deferred to ticket 14; synthetic evidence cannot
  establish installed skill behavior. Switching, transfer consent and redaction
  remain tickets 09–14; this command performs local extraction only.
- A Claude-specific `isSidechain` flag injected into Codex data is not treated as
  a supported Codex representation. Filters cover the native formats represented
  by existing adapters; new native formats require updated adapter validation.
- A metadata-only rollout can represent a valid empty session. Full coverage
  describes readable eligible conversation, without asserting that an empty
  native store contains unseen conversation.
- Adversarial repeated native metadata, arbitrary Claude filename/content
  mismatches, excessively nested JSON and filesystem symlink loops were not
  established as supported ordinary inputs by the review. They add no claim of
  adversarial-format hardening to this ticket.
- Existing transcript and usage compatibility is verified by the complete suite;
  the independent reviewer inspected callback preservation without independently
  rerunning the complete suite.
