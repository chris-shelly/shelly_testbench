"""US-009: Database class managing multiple tables tests."""

import os

from smalldoc_db.database import Database
from smalldoc_db.table import Table


class TestDatabase:
    """Tests for the Database class."""

    def test_creates_directory_if_missing(self, tmp_path):
        """Database constructor creates the directory when it does not exist."""
        db_path = tmp_path / "mydb"
        assert not db_path.exists()
        Database(str(db_path))
        assert db_path.is_dir()

    def test_constructor_accepts_existing_directory(self, tmp_path):
        """Database constructor works with an already-existing directory."""
        db_path = tmp_path / "mydb"
        db_path.mkdir()
        db = Database(str(db_path))
        assert db is not None

    def test_table_returns_table_instance(self, tmp_path):
        """Database.table() returns a Table object."""
        db = Database(str(tmp_path / "mydb"))
        t = db.table("users")
        assert isinstance(t, Table)

    def test_table_is_cached(self, tmp_path):
        """Database.table() returns the same Table instance on repeated calls."""
        db = Database(str(tmp_path / "mydb"))
        t1 = db.table("users")
        t2 = db.table("users")
        assert t1 is t2

    def test_table_backed_by_json_file(self, tmp_path):
        """Table is backed by <db_path>/<name>.json."""
        db_path = tmp_path / "mydb"
        db = Database(str(db_path))
        t = db.table("users")
        t.insert({"name": "Alice"})
        assert (db_path / "users.json").exists()

    def test_tables_lists_existing_tables(self, tmp_path):
        """Database.tables() lists table names from .json files."""
        db = Database(str(tmp_path / "mydb"))
        db.table("users").insert({"name": "Alice"})
        db.table("orders").insert({"item": "Book"})
        names = db.tables()
        assert sorted(names) == ["orders", "users"]

    def test_tables_empty_when_no_tables(self, tmp_path):
        """Database.tables() returns empty list when no tables exist."""
        db = Database(str(tmp_path / "mydb"))
        assert db.tables() == []

    def test_drop_removes_table_file(self, tmp_path):
        """Database.drop() deletes the table's JSON file."""
        db_path = tmp_path / "mydb"
        db = Database(str(db_path))
        db.table("users").insert({"name": "Alice"})
        assert (db_path / "users.json").exists()
        result = db.drop("users")
        assert result is True
        assert not (db_path / "users.json").exists()

    def test_drop_nonexistent_returns_false(self, tmp_path):
        """Database.drop() returns False for a table that does not exist."""
        db = Database(str(tmp_path / "mydb"))
        result = db.drop("nonexistent")
        assert result is False

    def test_drop_removes_from_tables_list(self, tmp_path):
        """After dropping, the table name no longer appears in tables()."""
        db = Database(str(tmp_path / "mydb"))
        db.table("users").insert({"name": "Alice"})
        db.drop("users")
        assert "users" not in db.tables()
