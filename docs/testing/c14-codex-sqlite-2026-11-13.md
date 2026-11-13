# C14-CODEX-02 — cold SQLite WAL access

**Disposition: triaged as a documented bounded runtime limitation.** Cold
read-only access remains unavailable on the tested SQLite runtime. No production
reader change is made, and this finding does not close C14 or the remaining
Claude/cross-Provider native acceptance groups.

Source: `8ab2f78`, `feature/codex-cli-support`. Tests and evidence were prepared
in an isolated local clone; no personal database or installed configuration was
read or changed. No native model request, push or merge was performed.

## Reproduction and boundary

The [original native observation](c14-codex-timestamp-fix-2026-11-11.md)
followed real Codex CLI exit. This investigation reproduces its exact SQLite
failure using disposable databases with the actual metadata/history schemas.

1. Populate a database, enable WAL and close its last writable connection.
2. Confirm the database remains and both sidecars are absent.
3. Make the first query through a `mode=ro` connection, before any writable
   connection can recreate the sidecars.

On Python 3.14.6 and system Python 3.9.6, both using SQLite 3.51.0, the first query
fails with `SQLITE_CANTOPEN` / `unable to open database file`. A DELETE-mode
database in the same writable directory reads successfully. The same WAL failure
was reproduced outside the sandbox with an explicitly escalated command:
`python3 /private/tmp/deskmate-c14-sqlite-probe-20261113.py`. The source of that
probe is preserved in the [JSON evidence](c14-codex-sqlite-2026-11-13.json).

Default, `unix` and `unix-excl` VFS probes did not resolve the failure. The
established boundary is cold WAL sidecar initialization on these installed
runtimes; the deeper SQLite/VFS implementation cause is not established. Both
Pythons share the same SQLite version, so this is not proof that every macOS or
SQLite runtime has the limitation.

## Supported degradation and recovery

- If history alone is inaccessible, the session retains its known metadata and
  usage while returning no messages and an explicit unavailable-history warning.
- If metadata is inaccessible too, session discovery may be incomplete and a
  requested session returns unavailable; that does not prove the native session
  or its history was deleted.
- `session-delta` exits 0 with `status: degraded`, unavailable coverage, zero
  included messages and guidance to continue from the Project card and Checks.
  The failed cold read leaves all native file bytes and the absence of sidecars
  unchanged. Project cards remain the durable source for continuation.
- The user may reopen the relevant Codex runtime normally and retry the read
  while its native SQLite sidecars exist. A fixture modeling that lifecycle
  recovered the original persisted messages. The original native observation
  also recovered after sidecars existed, but native-runtime reopening itself
  was not newly exercised in this triage; it is a recovery route, not a promise
  that every reopen or a later post-exit read succeeds.

Deskmate does not explicitly initialize or delete native sidecars, checkpoint the
database, switch it to DELETE mode, or open it read-write as a repair. Normal
SQLite read-only WAL coordination may initialize sidecars where supported.
`immutable=1` is not
a safe general fallback: it ignores live WAL and can silently omit committed
progress. SQLite's [WAL documentation](https://www.sqlite.org/wal.html#read_only_databases)
describes the sidecar requirements; its [URI documentation](https://www.sqlite.org/uri.html#uriimmutable)
explains that immutable connections disable locking/change detection.

Ordinary live `mode=ro` reads can update SHM read marks for coordination. The
live-WAL regression verifies unchanged main database and WAL bytes plus an
unchanged native file set; it deliberately does not require byte-identical SHM.

## Verification

Two public-command regression contracts cover cold metadata and history
independently, explicit unavailable coverage, preserved native bytes, lifecycle
recovery and fresh live-WAL metadata/messages. The cold test probes an independent
copy to characterize runtime capability; it also accepts complete reads on a
SQLite build that supports cold WAL rather than requiring an upstream defect.

The tests protect the existing bounded behavior; they are not evidence of a new
production fix. Mutation checks prove they reject read-write warming and a
general immutable fallback. The immutable mutation also returns old native usage
(`450` instead of committed WAL value `987`). Both mutations were reverted.

Independent review caught an intermediate harness capture using stale bytecode
from the intentional read-write mutation despite restored source. That capture
and its failed full-suite attempt were invalidated. Mutation checks now use a
fresh cache prefix per variant; evidence was regenerated with cache writes
disabled after removing the disposable adapter cache. The JSON preserves the
invalidated attempt separately from the accepted cold observations.

Baseline: **253/253 full-suite tests passed**, Python 3.14.6, 112.846 seconds,
ResourceWarnings treated as errors. Final cache-safe verification: **255/255**
full-suite tests passed in **100.052 seconds** on Python 3.14.6; **51/51** Codex
adapter/Session delta tests passed in **23.541 seconds** on Python 3.9.6. Both
commands set `PYTHONDONTWRITEBYTECODE=1` and treat ResourceWarnings as errors.
`git diff --check` passed. Independent review approved the corrected artifacts
with no remaining findings. Actual commands/results are in the JSON evidence.

Evidence: [observations and command results](c14-codex-sqlite-2026-11-13.json),
[mutation failures](c14-codex-sqlite-mutations-2026-11-13.json).
