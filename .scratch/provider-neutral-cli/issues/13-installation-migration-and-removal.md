# 13: Complete installation, migration and removal

**What to build:** Give the user one idempotent setup and removal experience that installs every compatible requested Provider, migrates current data safely, verifies integrations and preserves personal data unless explicitly purged.

**Blocked by:** 02: Detect and configure Providers; 04: Put Claude behind the Provider adapter; 05: Add the Codex Provider adapter; 06: Make logs and metrics Provider-aware; 12: Update reminders for both Providers.

**Status:** ready-for-agent

**Implementation:** complete

- [x] Setup installs one or both compatible Provider integrations according to detection and explicit overrides.
- [x] The stable command is made available from the user's normal shell path.
- [x] One portable skill source is linked into each installed Provider's skill location.
- [x] Existing hooks and unrelated configuration are preserved, and rerunning setup creates no duplicate Deskmate entries.
- [x] Setup migrates configuration, Project cards and logs atomically with backups and reports every migration.
- [x] Setup performs an end-to-end logging check and gives actionable guidance for approval or trust failures.
- [x] Removal deletes installed integrations but preserves Deskmate data by default.
- [x] Data purge is a separate choice, defaults to no and requires the exact confirmation `DELETE` interactively.
- [x] Non-interactive removal preserves data unless an explicit purge option is supplied.
- [x] Installation and removal tests operate only on isolated temporary homes.


## Comments

Implemented on 2026-11-09 by session `/root`, scoped to C13. Common
`deskmate setup`/`remove`, `install.sh` forwarding, shared setup skill, staged
Provider adapters, private backups/recoverable publication and verified native
service restoration. Requested overrides, hook/skill ownership, config/card/log
schemas and removal/purge behavior are exercised in temporary homes only.

Baseline 193/193; final full suite **224/224** on Python 3.14.6 with
ResourceWarnings as errors. All **31 installation scenarios** also pass on
system Python 3.9.6. One independent review completed; six Important findings
were reproduced RED and fixed GREEN. One detection-summary wording Minor is
documented for later. Evidence: `docs/testing/installation.md`. Native skill
discovery, runtime approval/delivery, actual desktop/calendar acceptance remain
pending under the existing model-request hold. No personal installation, push
or merge performed. C11 and C14 remain separate unfinished tickets.
