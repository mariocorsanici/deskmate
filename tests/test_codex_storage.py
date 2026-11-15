"""Read-only native SQLite recovery, using disposable databases only."""

from contextlib import closing
import os
import pathlib
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import codex_storage


class CodexStorageTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve()
        self.native = self.root / "native"
        self.native.mkdir()
        self.private = self.root / "private"
        self.private.mkdir()
        self.path = self.native / "state.sqlite"
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE example(value)")
            db.execute("INSERT INTO example VALUES (42)")
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA journal_mode=WAL")

    def files(self):
        return {p.name: p.read_bytes() for p in self.native.iterdir()}

    def private_directories(self):
        original = tempfile.TemporaryDirectory
        return mock.patch.object(codex_storage.tempfile, "TemporaryDirectory",
                                 side_effect=lambda **kwargs: original(dir=self.private, **kwargs))

    def test_cold_copy_is_private_disposable_and_keeps_native_files_untouched(self):
        before = self.files()
        with self.private_directories():
            with codex_storage.read_only(self.path) as db:
                self.assertEqual(db.execute("SELECT * FROM example").fetchall(), [(42,)])
                for directory in self.private.iterdir():
                    self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
                    for path in directory.iterdir():
                        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(list(self.private.iterdir()), [])
        self.assertEqual(self.files(), before)

    def test_cold_reader_preserves_files_when_sqlite_would_initialize_sidecars(self):
        before = self.files()
        open_db = codex_storage._open

        def sidecar_initializing_open(path, **kwargs):
            if path == self.path:
                # Model the native SQLite variant observed after real exit:
                # mode=ro succeeds but creates an empty WAL and a SHM file.
                path.with_name(path.name + "-wal").write_bytes(b"")
                path.with_name(path.name + "-shm").write_bytes(b"\0" * 32768)
                return open_db(path, immutable=True)
            return open_db(path, **kwargs)

        with self.private_directories(), mock.patch.object(codex_storage, "_open", sidecar_initializing_open):
            with codex_storage.read_only(self.path) as db:
                self.assertEqual(db.execute("SELECT * FROM example").fetchall(), [(42,)])
        self.assertEqual(set(self.files()), set(before))
        self.assertEqual(self.files(), before)
        self.assertEqual(list(self.private.iterdir()), [])

    def test_fresh_process_cold_reader_preserves_native_bytes_and_file_set(self):
        before = self.files()
        script = ("import pathlib,sys; sys.path.insert(0,sys.argv[1]); import codex_storage; "
                  "reader=codex_storage.read_only(pathlib.Path(sys.argv[2])); "
                  "db=reader.__enter__(); "
                  "assert db.execute('SELECT * FROM example').fetchall()==[(42,)]; "
                  "reader.__exit__(None,None,None)")
        result = subprocess.run([sys.executable, "-W", "error::ResourceWarning", "-c", script,
                                 str(pathlib.Path(codex_storage.__file__).parent), str(self.path)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.files(), before)

    def test_incomplete_live_sidecars_refuse_native_initialization(self):
        for suffix in ("-wal", "-shm", "-journal"):
            with self.subTest(suffix=suffix):
                sidecar = self.path.with_name(self.path.name + suffix)
                sidecar.write_bytes(b"incomplete native state")
                before = self.files()
                with self.assertRaises(sqlite3.Error):
                    with codex_storage.read_only(self.path):
                        self.fail("incomplete live sidecars must not be initialized or ignored")
                self.assertEqual(self.files(), before)
                sidecar.unlink()

    def test_live_reader_includes_committed_wal_without_copying(self):
        with closing(sqlite3.connect(self.path)) as native:
            native.execute("INSERT INTO example VALUES (99)")
            native.commit()
            before = self.files()
            with self.private_directories():
                with codex_storage.read_only(self.path) as db:
                    self.assertEqual(db.execute("SELECT * FROM example").fetchall(), [(42,), (99,)])
                    self.assertEqual(list(self.private.iterdir()), [])
            after = self.files()
            self.assertEqual(set(after), set(before))
            for name in before:
                if not name.endswith("-shm"):
                    self.assertEqual(after[name], before[name])

    def test_private_copy_is_cleaned_when_consumer_or_schema_fails(self):
        for sql in (None, "SELECT * FROM missing_table"):
            with self.subTest(sql=sql), self.private_directories():
                with self.assertRaises((sqlite3.Error, RuntimeError)):
                    with codex_storage.read_only(self.path) as db:
                        if sql:
                            db.execute(sql)
                        else:
                            raise RuntimeError("consumer failed")
                self.assertEqual(list(self.private.iterdir()), [])

    def test_sidecar_or_database_change_during_snapshot_query_rejects_completion(self):
        cold_bytes = self.path.read_bytes()
        for change in ("sidecar", "transient-sidecar", "replacement", "same-size-write"):
            with self.subTest(change=change), self.private_directories():
                # Fresh inode per race: SQLite may retain WAL state for an inode
                # already opened in this process even after its reader closes.
                self.path = self.native / (change + ".sqlite")
                self.path.write_bytes(cold_bytes)
                with self.assertRaises(sqlite3.OperationalError):
                    with codex_storage.read_only(self.path) as db:
                        self.assertEqual(db.execute("SELECT * FROM example").fetchall(), [(42,)])
                        if change in ("sidecar", "transient-sidecar"):
                            sidecar = self.path.with_name(self.path.name + "-wal")
                            sidecar.write_bytes(b"writer appeared")
                            if change == "transient-sidecar":
                                sidecar.unlink()
                        elif change == "replacement":
                            replacement = self.root / "replacement.sqlite"
                            shutil.copyfile(self.path, replacement)
                            os.replace(replacement, self.path)
                        else:
                            with self.path.open("r+b") as source:
                                source.seek(-1, os.SEEK_END)
                                source.write(b"\x00")
                for sidecar in self.native.glob("*-wal"):
                    sidecar.unlink()
                self.assertEqual(list(self.private.iterdir()), [])

    def test_corruption_does_not_create_native_files_or_leave_private_data(self):
        self.path.write_bytes(b"not a sqlite database")
        before = self.files()
        with self.private_directories(), self.assertRaises(sqlite3.DatabaseError):
            with codex_storage.read_only(self.path):
                self.fail("corrupt source must not yield a reader")
        self.assertEqual(self.files(), before)
        self.assertEqual(list(self.private.iterdir()), [])

    def test_writer_racing_every_copy_is_bounded_and_cleans_private_data(self):
        copy_file = codex_storage._copy_file
        copies = []

        def racing_copy(*args):
            copy_file(*args)
            copies.append(args[1])
            # Model a writer opening/closing without changing main DB bytes.
            sidecar = self.native / "state.sqlite-wal"
            sidecar.write_bytes(b"transient writer")
            sidecar.unlink()

        with self.private_directories(), mock.patch.object(codex_storage, "_copy_file", racing_copy):
            with self.assertRaises(sqlite3.OperationalError):
                with codex_storage.read_only(self.path):
                    self.fail("racing copy must never expose stale rows")
        self.assertLessEqual(len(copies), 3)
        self.assertEqual(list(self.private.iterdir()), [])

    def test_writer_between_private_open_and_yield_closes_reader(self):
        open_db = codex_storage._open
        readers = []

        def racing_open(path, **kwargs):
            db = open_db(path, **kwargs)
            if kwargs.get("immutable"):
                readers.append(db)
                (self.native / "state.sqlite-wal").write_bytes(b"writer appeared")
            return db

        with self.private_directories(), mock.patch.object(codex_storage, "_open", racing_open):
            with self.assertRaises(sqlite3.OperationalError):
                with codex_storage.read_only(self.path):
                    self.fail("writer race must be rejected before data is exposed")
        self.assertTrue(readers)
        for db in readers:
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute("SELECT 1")
        self.assertEqual(list(self.private.iterdir()), [])

    def test_access_failure_with_live_sidecars_never_uses_an_immutable_copy(self):
        open_db = codex_storage._open
        with closing(sqlite3.connect(self.path)) as writer:
            writer.execute("INSERT INTO example VALUES (99)")
            writer.commit()
            before = self.files()

            def unavailable_native(path, **kwargs):
                if path == self.path:
                    raise sqlite3.OperationalError("unable to open database file")
                return open_db(path, **kwargs)

            with self.private_directories(), mock.patch.object(codex_storage, "_open", unavailable_native):
                with self.assertRaises(sqlite3.OperationalError):
                    with codex_storage.read_only(self.path):
                        self.fail("a live WAL must not be ignored after a reader failure")
            self.assertEqual(self.files(), before)
            self.assertEqual(list(self.private.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
