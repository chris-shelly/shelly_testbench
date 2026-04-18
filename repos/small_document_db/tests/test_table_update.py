"""US-006: Table update operation tests."""

from smalldoc_db.table import Table


class TestTableUpdate:
    """Tests for Table.update()."""

    def test_update_existing_returns_true(self, tmp_path):
        """update() returns True when the document exists."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice", "age": 30})
        result = table.update(doc_id, {"age": 31})
        assert result is True

    def test_update_merges_changes(self, tmp_path):
        """update() merges changes into the existing document."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice", "age": 30})
        table.update(doc_id, {"age": 31, "city": "NYC"})
        doc = table.get(doc_id)
        assert doc["name"] == "Alice"  # untouched field
        assert doc["age"] == 31  # updated field
        assert doc["city"] == "NYC"  # new field

    def test_update_missing_returns_false(self, tmp_path):
        """update() returns False when the ID does not exist."""
        table = Table(str(tmp_path / "t.json"))
        result = table.update("nonexistent", {"name": "Bob"})
        assert result is False

    def test_update_cannot_change_id(self, tmp_path):
        """update() does not allow changing the _id field."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice"})
        table.update(doc_id, {"_id": "new-id", "name": "Bob"})
        doc = table.get(doc_id)
        assert doc["_id"] == doc_id  # _id unchanged
        assert doc["name"] == "Bob"  # other changes applied

    def test_update_persists_to_disk(self, tmp_path):
        """Updated document is persisted and survives re-loading."""
        path = str(tmp_path / "t.json")
        table = Table(path)
        doc_id = table.insert({"name": "Alice", "age": 30})
        table.update(doc_id, {"age": 31})
        # Re-open
        table2 = Table(path)
        doc = table2.get(doc_id)
        assert doc["age"] == 31
