# 03: Migrate to shared Project cards

**What to build:** Give each project one provider-neutral Project card that safely preserves the latest Checkpoint and current Checks regardless of which Provider owns the Work session.

**Blocked by:** 01: Introduce the provider-neutral command.

**Status:** ready-for-agent

**Implementation:** complete

- [x] A project key combines a readable slug with a hash of its canonical path.
- [x] Project cards remain readable Markdown with restricted, validated metadata for schema, revision and Work session ownership.
- [x] Card updates use locking, revision checks and atomic replacement.
- [x] A stale writer rereads current state instead of silently overwriting it.
- [x] Existing Claude Project cards migrate to shared storage with a recoverable backup.
- [x] Existing Claude access resolves to the shared Project card without creating a second source of truth.
- [x] Repeating migration is safe and does not duplicate or discard content.
- [x] Unsupported future card schemas stop before mutation.


## Comments

Implemented `deskmate card locate|list|write|migrate` with strict metadata,
canonical project identities, stable locks, revision conflicts and atomic
replacement. Migration preserves byte-for-byte content-addressed backups and
repairs interrupted Claude symlink installation. Skills and Checks now use
shared storage. Direct manual edits bypass the update protocol, as documented.

Validation: `python3 -m unittest discover -q` — 53 tests pass (36 existing,
17 new). Independent review reproduced and fixed legacy future-schema mutation,
latest-Checkpoint ownership and executable-mode regressions. No real project
cards were migrated; all migration tests use temporary homes and data roots.
