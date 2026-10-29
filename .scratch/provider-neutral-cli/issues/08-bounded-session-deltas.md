# 08: Extract bounded Session deltas

**What to build:** Recover recent unrecorded progress from either Provider without loading an entire transcript, and disclose exactly how much context was selected or omitted.

**Blocked by:** 04: Put Claude behind the Provider adapter; 05: Add the Codex Provider adapter.

**Status:** ready-for-agent

- [ ] Each adapter extracts only messages after the latest Checkpoint.
- [ ] Metadata and raw tool output are excluded from the Session delta.
- [ ] Default limits are 12 messages and 6,000 characters.
- [ ] Configuration can lower or raise the defaults.
- [ ] One command can override limits without mutating configuration.
- [ ] Selection retains useful early context and the most recent context when truncation is required.
- [ ] Output declares included and omitted counts, character size, coverage and truncation.
- [ ] Missing, malformed or unreadable transcripts produce a structured degraded result rather than stopping the Daily loop.

