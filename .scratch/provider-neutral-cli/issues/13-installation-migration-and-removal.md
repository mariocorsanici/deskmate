# 13: Complete installation, migration and removal

**What to build:** Give the user one idempotent setup and removal experience that installs every compatible requested Provider, migrates current data safely, verifies integrations and preserves personal data unless explicitly purged.

**Blocked by:** 02: Detect and configure Providers; 04: Put Claude behind the Provider adapter; 05: Add the Codex Provider adapter; 06: Make logs and metrics Provider-aware; 12: Update reminders for both Providers.

**Status:** ready-for-agent

- [ ] Setup installs one or both compatible Provider integrations according to detection and explicit overrides.
- [ ] The stable command is made available from the user's normal shell path.
- [ ] One portable skill source is linked into each installed Provider's skill location.
- [ ] Existing hooks and unrelated configuration are preserved, and rerunning setup creates no duplicate Deskmate entries.
- [ ] Setup migrates configuration, Project cards and logs atomically with backups and reports every migration.
- [ ] Setup performs an end-to-end logging check and gives actionable guidance for approval or trust failures.
- [ ] Removal deletes installed integrations but preserves Deskmate data by default.
- [ ] Data purge is a separate choice, defaults to no and requires the exact confirmation `DELETE` interactively.
- [ ] Non-interactive removal preserves data unless an explicit purge option is supplied.
- [ ] Installation and removal tests operate only on isolated temporary homes.

