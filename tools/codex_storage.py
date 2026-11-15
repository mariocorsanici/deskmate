"""Read provider-owned SQLite, with disposable recovery for cold WAL files.

An immutable reader is safe only on our private copy: native committed WAL
must always be read by ordinary SQLite. No native writable connection is used.
"""

from contextlib import closing, contextmanager
import os
import pathlib
import sqlite3
import stat
import tempfile


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _sidecars(path):
    present = set()
    for suffix in ("-wal", "-shm", "-journal"):
        try:
            path.with_name(path.name + suffix).lstat()
        except FileNotFoundError:
            continue
        present.add(suffix)
    return present


def _cold_state(path):
    # lstat also rejects dangling sidecar symlinks. Directory timestamps detect
    # a WAL created and removed between observations, including no-op writers.
    parent = path.parent.stat()
    if _sidecars(path):
        raise OSError("Native SQLite sidecars appeared during cold recovery.")
    source = path.stat()
    if not stat.S_ISREG(source.st_mode):
        raise OSError("Native SQLite source is not a regular file.")
    return (_identity(source), (parent.st_dev, parent.st_ino,
                               parent.st_mtime_ns, parent.st_ctime_ns))


def _copy_file(path, target, expected):
    # Bound the copy to the observed size even if a writer grows the file.
    with path.open("rb") as source, target.open("xb") as destination:
        os.chmod(target, 0o600)
        if _identity(os.fstat(source.fileno())) != expected:
            raise OSError("Native SQLite source was replaced before copying.")
        remaining = expected[3]
        while remaining:
            data = source.read(min(1024 * 1024, remaining))
            if not data:
                raise OSError("Native SQLite source changed while copying.")
            destination.write(data)
            remaining -= len(data)
        if _identity(os.fstat(source.fileno())) != expected:
            raise OSError("Native SQLite source changed while copying.")


def _open(path, *, immutable=False):
    uri = path.as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")
    db = sqlite3.connect(uri, uri=True, timeout=1)
    try:
        # connect is lazy; force access/schema failures before yielding so a
        # consumer is never replayed (and messages are never delivered twice).
        db.execute("PRAGMA schema_version").fetchone()
    except BaseException:
        db.close()
        raise
    return db


@contextmanager
def read_only(path):
    """Yield a reader; refuse unstable cold copies instead of claiming coverage.

    Existing WAL+SHM use ordinary mode=ro for live coordination. A sidecar-free
    source is copied without opening native SQLite: some runtimes initialize
    sidecars even in mode=ro. Cold preparation allows three bounded attempts;
    the source and its directory must stay stable through consumption.
    """
    path = pathlib.Path(path).resolve()
    sidecars = _sidecars(path)
    if sidecars:
        if sidecars != {"-wal", "-shm"}:
            raise sqlite3.OperationalError("Native SQLite sidecars are incomplete or unsupported.")
        with closing(_open(path)) as db:
            yield db
        return

    with tempfile.TemporaryDirectory(prefix="deskmate-codex-sqlite-") as directory:
        private = pathlib.Path(directory)
        os.chmod(private, 0o700)
        for attempt in range(3):
            target = private / (str(attempt) + ".sqlite")
            try:
                before = _cold_state(path)
                _copy_file(path, target, before[0])
                if _cold_state(path) != before:
                    raise OSError("Native SQLite changed during cold recovery.")
                db = _open(target, immutable=True)
                try:
                    if _cold_state(path) != before:
                        raise OSError("Native SQLite changed while opening its snapshot.")
                except BaseException:
                    db.close()
                    raise
            except OSError as error:
                target.unlink(missing_ok=True)
                if attempt == 2:
                    raise sqlite3.OperationalError("Native SQLite cold snapshot is unstable or unavailable.") from error
                continue
            break
        with closing(db):
            yield db
            try:
                if _cold_state(path) != before:
                    raise OSError("Native SQLite changed while reading its snapshot.")
            except OSError as error:
                raise sqlite3.OperationalError("Native SQLite changed during cold history read.") from error
