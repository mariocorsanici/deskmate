# Cold Codex SQLite history recovery

Task 2 of the [pre-merge reliability plan](../superpowers/plans/2026-11-15-premerge-reliability.md)
implements a repair for the previously documented
[cold WAL limitation](c14-codex-sqlite-2026-11-13.md). Complete cold metadata and
persisted messages are now required by the public-command regression; degraded
output alone no longer satisfies that regression.

## Reproduction and repair

On Python 3.14.6 / SQLite 3.51.0, a disposable database containing a committed
row, switched to WAL and closed by its last writable connection, has no WAL/SHM
sidecars. An ordinary `mode=ro` query fails with `SQLITE_CANTOPEN` / `unable to
open database file`. A private copy queried with `mode=ro&immutable=1` returns
the persisted row (`42`); all native bytes and native filenames remain unchanged.
This reproduces the earlier probe with the current installed runtime.

A subsequent actual native post-exit run exposed a second installed-runtime
behavior: the public command selected system Python 3.9 through its PATH,
returned complete history, and left an empty native WAL plus a 32768-byte SHM.
This violated file-set preservation even though metadata/messages were correct.
A successful ordinary read therefore cannot be used to decide whether cold
recovery is necessary. The earlier failure-triggered fallback is superseded.

`tools/codex_storage.py` owns the connection boundary used by metadata and
paginated history. A source with no WAL/SHM/rollback-journal paths goes directly
to a stable private snapshot without opening native SQLite. A complete existing
WAL+SHM pair uses ordinary `mode=ro`, preserving committed live WAL data and
SQLite coordination. Incomplete sidecars or a rollback journal cause explicit
refusal rather than initialization or an immutable native read. Native access
errors with existing live sidecars propagate; they never permit ignoring WAL.
Connections force a schema query before a consumer receives them, so lazy
failure cannot cause a consumer to be replayed.

Cold recovery requires absent WAL, SHM and rollback-journal paths, including
dangling symlinks. It copies the native main file through a read-only descriptor
to a private directory (0700) and private file (0600), bounded to the observed
source size. Descriptor and pathname device/inode/mode/size/mtime/ctime must
agree before and after copying. Parent directory identity, mtime and ctime must
also remain unchanged: this catches a writer creating and then removing
sidecars even when main database bytes do not change.

Only this private copy is opened immutable. The source and directory are
validated again before exposing the copy and after the consumer finishes.
Changing/replacing the native file or adding/removing sidecars prevents a
successful completed read. Preparation allows three immediate attempts; a
consumer is never replayed. All connections close and all private files are
removed on success, schema/query errors, copy errors and race refusal. Neither
native writable initialization nor a persistent transcript cache is used.

## Verification

The public cold metadata/history regression first failed twice with
`degraded != ok` against the previous implementation. It now requires `ok`,
`coverage.status == full`, persisted messages, metadata and identical native
bytes/file sets. Reopening the fixture with its native writable connection is
still tested as a separate lifecycle transition. The existing live-WAL command
regression requires committed usage `987` and a message present only in WAL;
main/WAL bytes and the native file set remain unchanged. SQLite may update SHM
read marks during ordinary live coordination.

Eleven new storage tests cover private permission modes and cleanup, live WAL,
corruption, unsupported query/schema cleanup, bounded writer races, a writer
appearing between private-open and yield, and changes during consumption:
persistent sidecar, transient sidecar, main-file replacement and same-size
write. A forced native access failure while a real writer retains live WAL
must refuse a cold snapshot. Added regressions model the observed SQLite variant
that succeeds while creating empty WAL/SHM, exercise a fresh-process cold read,
and refuse each incomplete sidecar state. The sidecar-creation regression first
failed on the added native files despite returning the correct persisted row.
Race injection performs real filesystem changes
at the copy/open boundary. Each consumption-race case uses a fresh inode to
avoid SQLite's per-process retained WAL state affecting later cases.

One test exposed a leaked private reader when a sidecar appeared immediately
after opening its snapshot; it failed with an executable connection plus a
ResourceWarning, then passed after explicit exception-path closing.

Focused verification, with bytecode writes disabled and ResourceWarnings
treated as errors:

| Command | Result |
| --- | --- |
| `python3 -W error::ResourceWarning -m unittest discover -s tests -p 'test_codex*.py'` | 32 passed, Python 3.14.6, 5.561s |
| `/usr/bin/python3 -W error::ResourceWarning -m unittest discover -s tests -p 'test_codex*.py'` | 32 passed, Python 3.9.6, 12.305s |
| `python3 -W error::ResourceWarning -m unittest discover -s tests -p test_codex_storage.py` | 8 passed after final fixture isolation, 0.036s |
| `/usr/bin/python3 -W error::ResourceWarning -m unittest discover -s tests -p test_codex_storage.py` | 8 passed after final fixture isolation, 0.033s |

After the proactive-cold correction:

| Command | Result |
| --- | --- |
| `python3 -W error::ResourceWarning -m unittest discover -s tests -p test_codex_storage.py` | 11 passed, Python 3.14.6, 0.135s |
| `/usr/bin/python3 -W error::ResourceWarning -m unittest discover -s tests -p test_codex_storage.py` | 11 passed, Python 3.9.6, 0.060s |
| `python3 -W error::ResourceWarning -m unittest discover -s tests -p 'test_codex*.py'` | 35 passed, Python 3.14.6, 6.311s |
| `/usr/bin/python3 -W error::ResourceWarning -m unittest discover -s tests -p 'test_codex*.py'` | 35 passed, Python 3.9.6, 13.174s |

Focused independent review found no actionable storage issues and independently
ran the 11 storage tests. Cleanup and race-refusal paths were reviewed; native
GUI acceptance remains owned by the parent integration task.

The sidecar-initialization RED is recorded in
`evidence/sqlite-red-native-sidecar-creation.log`; new focused results use
`sqlite-proactive-*.log`. The preceding 32-test and broad results describe the
initial failure-triggered version and are superseded for the corrected bytes.

In-memory mutations, without editing the shared production source, were
rejected: native immutable reads omitted the WAL-only row; removing directory
transition checks exposed a transient writer; removing final validation
accepted all four consumption races. The public RED and cleanup RED, final
focused logs, probe and mutation logs are captured as `evidence/sqlite-*.log` in
the isolated pre-merge execution workspace. Intermediate fixture failures were
corrected: the coverage vocabulary is `full`, and macOS temporary paths must be
resolved before injecting a path-specific native access failure. They are not
accepted product failures or evidence of a repaired SQLite defect.

An integrated full suite is owned by the parent task at its stable combined
boundary. A broad run started during parallel reminder/startup work is
provisional and cannot establish final branch acceptance: it passed 294 tests
in 135.311s on Python 3.14.6 with ResourceWarnings treated as errors and bytecode
writes disabled (`sqlite-full-suite-314.log`).

## Limits and remaining integration

The cold nonmutation guarantee applies to a stable sidecar-free snapshot.
Ordinary live WAL access still performs SQLite coordination: SHM read marks may
change. A native writer closing and removing its live pair between preflight
and the ordinary SQLite open remains a live coordination race; this helper does
not implement a separate SQLite locking protocol or promise an unchanged live
sidecar set across external writer transitions.

Unknown schemas, corruption, unsupported access and continuously changing
native databases still report explicit degradation. Unrelated changes in the
same native directory can conservatively refuse a cold snapshot. The stability
checks rely on the local filesystem's device/inode and nanosecond change
metadata; this is a refusal strategy for normal native writer races, not a
defense against a privileged actor forging filesystem state.

The disposable actual-schema and helper fixtures alone do not establish native
GUI acceptance. The parent integration task subsequently completed actual
Codex new/resume and normal exit, then read all four expected native conversation
messages through public `session` and `session-delta` with full coverage. History
sidecars were absent; native main/WAL bytes and the filename set stayed unchanged
(metadata SHM coordination bytes excluded). The combined final candidate passed
308 tests; 131 selected checks passed on system Python. Native identity, hashes,
cleanup and limits are preserved in
[integrated verification](premerge-reliability-2026-11-15.md) and its JSON.
