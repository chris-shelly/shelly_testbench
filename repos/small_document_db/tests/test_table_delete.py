"""US-008: Table delete operation tests."""

from smalldoc_db.table import Table


class TestTableDelete:
    """Tests for Table.delete()."""

    def test_delete_existing_returns_true(self, tmp_path):
        """delete() returns True when the document exists and is removed."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice"})
        result = table.delete(doc_id)
        assert result is True

    def test_delete_missing_returns_false(self, tmp_path):
        """delete() returns False when the ID does not exist."""
        table = Table(str(tmp_path / "t.json"))
        result = table.delete("nonexistent")
        assert result is False

    def test_delete_then_get_returns_none(self, tmp_path):
        """After deletion, get() returns None for that ID."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice"})
        table.delete(doc_id)
        assert table.get(doc_id) is None

    def test_delete_persists_to_disk(self, tmp_path):
        """Deletion is persisted; re-loading the table shows document is gone."""
        path = str(tmp_path / "t.json")
        table = Table(path)
        doc_id = table.insert({"name": "Alice"})
        table.delete(doc_id)
        # Re-open
        table2 = Table(path)
        assert table2.get(doc_id) is None

    def test_delete_does_not_affect_other_documents(self, tmp_path):
        """Deleting one document does not affect other documents."""
        table = Table(str(tmp_path / "t.json"))
        id1 = table.insert({"name": "Alice"})
        id2 = table.insert({"name": "Bob"})
        table.delete(id1)
        assert table.get(id1) is None
        assert table.get(id2) is not None
        assert table.get(id2)["name"] == "Bob"
