"""US-005: Table get-by-id read operation tests."""

from smalldoc_db.table import Table


class TestTableGet:
    """Tests for Table.get()."""

    def test_get_existing_document(self, tmp_path):
        """get() returns the document for an existing ID."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice", "age": 30})
        result = table.get(doc_id)
        assert result is not None
        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_get_missing_id_returns_none(self, tmp_path):
        """get() returns None for an ID that does not exist."""
        table = Table(str(tmp_path / "t.json"))
        result = table.get("nonexistent-id")
        assert result is None

    def test_get_includes_id_field(self, tmp_path):
        """Returned document includes the _id field."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice"})
        result = table.get(doc_id)
        assert "_id" in result
        assert result["_id"] == doc_id

    def test_get_returns_copy_mutation_isolation(self, tmp_path):
        """Mutating the returned document does not affect the stored data."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.insert({"name": "Alice"})
        result = table.get(doc_id)
        result["name"] = "MODIFIED"
        # Re-read should still have original value
        result2 = table.get(doc_id)
        assert result2["name"] == "Alice"

    def test_get_after_multiple_inserts(self, tmp_path):
        """get() retrieves the correct document when multiple exist."""
        table = Table(str(tmp_path / "t.json"))
        id1 = table.insert({"name": "Alice"})
        id2 = table.insert({"name": "Bob"})
        assert table.get(id1)["name"] == "Alice"
        assert table.get(id2)["name"] == "Bob"
