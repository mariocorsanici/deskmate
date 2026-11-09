# 08: Extract bounded Session deltas

**What to build:** Recover recent unrecorded progress from either Provider without loading an entire transcript, and disclose exactly how much context was selected or omitted.

**Blocked by:** 04: Put Claude behind the Provider adapter; 05: Add the Codex Provider adapter.

**Status:** ready-for-agent

**Implementation:** complete (automated acceptance; authenticated native acceptance remains ticket 14).

- [x] Each adapter extracts only messages after the latest Checkpoint.
- [x] Metadata and raw tool output are excluded from the Session delta.
- [x] Default limits are 12 messages and 6,000 characters.
- [x] Configuration can lower or raise the defaults.
- [x] One command can override limits without mutating configuration.
- [x] Selection retains useful early context and the most recent context when truncation is required.
- [x] Output declares included and omitted counts, character size, coverage and truncation.
- [x] Missing, malformed or unreadable transcripts produce a structured degraded result rather than stopping the Daily loop.


## Comments

2026-11-06: Added `deskmate session-delta` and streaming consumers to both Provider
adapters. The shared selector applies configurable/one-off 12-message and
6,000-character defaults, keeps early and recent conversation, and reports
included/omitted counts, characters, truncation and full/partial/unavailable
coverage. The command is read-only and does not launch or transfer to a Provider.

The latest saved Checkpoint comes from the shared Project card only when Provider
and session ownership match. Cancelled native checkpoint prompts do not erase
unsaved context. Legacy minute timestamps disclose estimated coverage; an
explicit timezone-aware `--after` can provide a precise boundary. Absent matching
saved state, the result states session-start coverage. Corrupt/unreadable native
history returns degraded success with warnings; unknown timestamps cannot be
misrepresented as confirmed post-Checkpoint work.

Public-command acceptance uses isolated synthetic Claude JSONL, Codex rollout
JSONL and Codex paginated SQLite stores. Initial tests failed on the missing
command; an additional native-index identity regression exposed another
session's messages being emitted before the index check. The selector now rejects
mismatched native identity before retaining any message. No personal data or
authenticated model requests were used.

2026-11-09 final verification: 157 tests pass, no skips, ResourceWarnings as
errors. All 25 dedicated tests also pass on macOS system Python. Whitespace
checks pass. One independent review found four Important issues, each reproduced
with RED/GREEN public regressions and corrected before the final suite. See
`docs/testing/bounded-session-deltas.md` for complete evidence and scope decisions.
