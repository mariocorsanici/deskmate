# 05: Add the Codex Provider adapter

**What to build:** Make Codex CLI an equal local Provider that can participate in the same Daily loop and shared Project cards using Codex-native skill discovery and session behavior.

**Blocked by:** 01: Introduce the provider-neutral command; 02: Detect and configure Providers; 03: Migrate to shared Project cards.

**Status:** ready-for-agent

- [ ] The Codex adapter can discover Work sessions for a requested period.
- [ ] It can read usage information and bounded conversation data from synthetic Codex sessions.
- [ ] It can launch a new Work session and resume a Codex-owned Work session.
- [ ] Hook configuration merges Deskmate entries idempotently and preserves unrelated user configuration.
- [ ] Setup explains any Codex trust or hook approval required and can verify that logging works.
- [ ] Codex discovers the same portable skills and invokes them with its native dollar syntax.
- [ ] A Codex-only Daily loop works through the provider-neutral command.
- [ ] Adapter failures return structured errors without corrupting shared state.

