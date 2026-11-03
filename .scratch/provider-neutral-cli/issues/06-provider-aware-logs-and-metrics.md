# 06: Make logs and metrics Provider-aware

**What to build:** Preserve historical Deskmate activity while identifying which Provider owns every new event and keeping incompatible raw Claude and Codex measurements distinct.

**Blocked by:** 01: Introduce the provider-neutral command; 02: Detect and configure Providers.

**Status:** Implementation complete

- [x] New log entries include Provider identity.
- [x] Work sessions are identified by Provider plus Provider-native session ID.
- [x] Historical log entries migrate atomically and are attributed to Claude.
- [x] Migration creates a backup and preserves existing rows and meanings.
- [x] Repeating migration is safe and does not duplicate rows.
- [x] Unsupported future log schemas stop before mutation.
- [x] Raw Claude and Codex usage remains separately reportable and is never combined as if directly comparable.


## Comments

- Implemented in `56ec840`: activity rows retain the original eleven columns and add `schema_version=1` and `provider`. Historical callers default to Claude. Migration validates before creating a lock, backs up exact source bytes, serializes writers and atomically replaces the CSV. Repeat migration does not add rows or backups; malformed/future rows stop without mutation. Empty files with the current header contain no declared future version and are accepted.
- `hook-event --provider claude|codex` consumes native stdin JSON, recognizes native skill syntax, requires Claude's Skill tool for tool events and returns native JSON. Stop preserves Claude's historical per-skill token meanings and replaces native usage snapshots under `data/usage/{provider}.json`; provider plus exact native session ID remains the identity. Snapshot schemas are validated before writes. Repeated Stop does not add cumulative counters again.
- `metrics` reads adapter metadata and `read_usage` only, excludes conversation content, keeps Claude per-skill usage distinct from native session usage, partitions raw reports by Provider, labels unavailable-transcript snapshots `cached` and prefers fresh native counters. Claude session statistics ignore Codex ratings with matching native IDs.
- Acceptance verified through `bin/deskmate` with isolated HOME, CODEX_HOME/data and synthetic transcripts: 15 activity tests passed, including legacy row/meaning preservation, exact backups, idempotency, concurrent writers, invalid/future schema refusal, native raw counters, provider-ID collisions, Stop snapshots, content omission and cached/fresh behavior.
- Full combined validation: `python3 -m unittest discover -v` passed 99 tests in 27.528s in `/private/tmp/deskmate-06-validation-oqhnbpdk`, containing ticket06 plus the current ticket04 facade/Claude adapter and ticket05 Codex adapter/skill metadata. These dependency files were copied only into the disposable runtime. Central branch integration and its final rerun remain with the coordinating agent. Native runtime approval/live user-session acceptance was not exercised; no real user data/configuration was read or changed. Nonfailing Python 3.14 SQLite resource warnings were relayed to ticket05.
