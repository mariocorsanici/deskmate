# 11: Make the retrospective progressive

**What to build:** Keep retrospective context small by analysing durable data first, letting the user select relevant Work sessions, and reading bounded Session deltas only where they add value.

**Blocked by:** 03: Migrate to shared Project cards; 06: Make logs and metrics Provider-aware; 08: Extract bounded Session deltas.

**Status:** ready-for-agent

- [ ] The initial retrospective uses metrics, Handoffs, Project cards and logs without reading conversation messages.
- [ ] All available candidate Work sessions are listed with Provider identity.
- [ ] Deskmate recommends at most five candidates and explains each recommendation.
- [ ] The user can add, remove or replace candidates before any Session delta is read.
- [ ] Selected sessions are read with the configured bounded limits.
- [ ] The user can deepen one unclear session at a time with an explicit one-off limit.
- [ ] Transcript adapter failure degrades the affected analysis without stopping the retrospective.
- [ ] Provider-specific raw metrics remain visibly distinct in the result.

