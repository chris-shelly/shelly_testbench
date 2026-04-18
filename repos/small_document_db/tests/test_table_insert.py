"""US-004: Table class with insert operation tests."""

import pytest

from smalldoc_db.table import Table


class TestTableInsert:
    """Tests for Table.insert()."""

    def test_insert_returns_string_id(self, tmp_path):
        """insert() returns a string ID."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice"})
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0

    def test_insert_auto_generates_id(self, tmp_path):
        """insert() generates a unique ID when doc has no _id."""
        table = Table(str(tmp_path / "t.json"))
        id1 = table.insert({"name": "Alice"})
        id2 = table.insert({"name": "Bob"})
        assert id1 != id2

    def test_insert_with_user_supplied_id(self, tmp_path):
        """insert() uses the _id from the document if provided."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"_id": "custom-1", "name": "Alice"})
        assert doc_id == "custom-1"

    def test_insert_duplicate_id_raises_value_error(self, tmp_path):
        """insert() raises ValueError when _id already exists."""
        table = Table(str(tmp_path / "t.json"))
        table.insert({"_id": "dup", "name": "Alice"})
        with pytest.raises(ValueError):
            table.insert({"_id": "dup", "name": "Bob"})

    def test_insert_persists_to_disk(self, tmp_path):
        """Inserted document is immediately available after re-loading."""
        path = str(tmp_path / "t.json")
        table = Table(path)
        doc_id = table.insert({"name": "Alice"})
        # Re-open from same path
        table2 = Table(path)
        result = table2.get(doc_id)
        assert result is not None
        assert result["name"] == "Alice"

    def test_insert_stores_document_fields(self, tmp_path):
        """All fields from the inserted document are stored."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice", "age": 30, "active": True})
        result = table.get(doc_id)
        assert result["name"] == "Alice"
        assert result["age"] == 30
        assert result["active"] is True
