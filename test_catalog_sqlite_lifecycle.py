"""Regression: SQLite migration backup handles must close on Windows.

sqlite3.Connection used with "with" commits/rolls back but does not close.
Windows will reject TemporaryDirectory cleanup if the backup connection stays open.
This test checks explicit closure on every platform, including Linux CI.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import autocite_catalog
from autocite_catalog import Catalog


class TrackingConnection(sqlite3.Connection):
    def close(self):
        self.was_closed = True
        super().close()


class CatalogSQLiteLifecycleTests(unittest.TestCase):
    def test_backup_connection_closes_before_temporary_directory_cleanup(self):
        instances = []
        original_connect = sqlite3.connect

        def track_connection(*args, **kwargs):
            kwargs["factory"] = TrackingConnection
            connection = original_connect(*args, **kwargs)
            instances.append((str(args[0]), connection))
            return connection

        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "catalog.sqlite3"
            with patch.object(autocite_catalog.sqlite3, "connect", side_effect=track_connection):
                catalog = Catalog(db_path)
                try:
                    archives = [
                        conn for name, conn in instances
                        if name.endswith("_backup_pre_0.4.sqlite3")
                    ]
                    self.assertEqual(len(archives), 1)
                    self.assertTrue(
                        getattr(archives[0], "was_closed", False),
                        "SQLite migration backup was not explicitly closed",
                    )
                finally:
                    catalog.close()

            self.assertTrue(
                all(getattr(conn, "was_closed", False) for _, conn in instances),
                "All SQLite handles must close before removing test files",
            )


if __name__ == "__main__":
    unittest.main()
