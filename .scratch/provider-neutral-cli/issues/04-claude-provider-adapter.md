# 04: Put Claude behind the Provider adapter

**What to build:** Preserve the Claude Code experience while routing Claude-specific behavior through the shared Provider contract, proving that the new architecture can run an existing Daily loop end to end.

**Blocked by:** 01: Introduce the provider-neutral command; 03: Migrate to shared Project cards.

**Status:** ready-for-agent

- [ ] The Claude adapter can discover Work sessions for a requested period.
- [ ] It can read usage information and bounded conversation data from synthetic Claude sessions.
- [ ] It can launch a new Work session and resume a Claude-owned Work session.
- [ ] Hook configuration merges Deskmate entries idempotently and preserves unrelated user configuration.
- [ ] Claude continues to discover and invoke the portable skills with its native slash syntax.
- [ ] A Claude-only Daily loop works through the provider-neutral command.
- [ ] Adapter failures return structured errors without corrupting shared state.

