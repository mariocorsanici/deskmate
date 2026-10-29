# 03: Migrate to shared Project cards

**What to build:** Give each project one provider-neutral Project card that safely preserves the latest Checkpoint and current Checks regardless of which Provider owns the Work session.

**Blocked by:** 01: Introduce the provider-neutral command.

**Status:** ready-for-agent

- [ ] A project key combines a readable slug with a hash of its canonical path.
- [ ] Project cards remain readable Markdown with restricted, validated metadata for schema, revision and Work session ownership.
- [ ] Card updates use locking, revision checks and atomic replacement.
- [ ] A stale writer rereads current state instead of silently overwriting it.
- [ ] Existing Claude Project cards migrate to shared storage with a recoverable backup.
- [ ] Existing Claude access resolves to the shared Project card without creating a second source of truth.
- [ ] Repeating migration is safe and does not duplicate or discard content.
- [ ] Unsupported future card schemas stop before mutation.

