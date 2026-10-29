# 06: Make logs and metrics Provider-aware

**What to build:** Preserve historical Deskmate activity while identifying which Provider owns every new event and keeping incompatible raw Claude and Codex measurements distinct.

**Blocked by:** 01: Introduce the provider-neutral command; 02: Detect and configure Providers.

**Status:** ready-for-agent

- [ ] New log entries include Provider identity.
- [ ] Work sessions are identified by Provider plus Provider-native session ID.
- [ ] Historical log entries migrate atomically and are attributed to Claude.
- [ ] Migration creates a backup and preserves existing rows and meanings.
- [ ] Repeating migration is safe and does not duplicate rows.
- [ ] Unsupported future log schemas stop before mutation.
- [ ] Raw Claude and Codex usage remains separately reportable and is never combined as if directly comparable.

