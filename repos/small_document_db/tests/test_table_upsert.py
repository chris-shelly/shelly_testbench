"""US-007: Table upsert operation tests."""

from smalldoc_db.table import Table


class TestTableUpsert:
    """Tests for Table.upsert()."""

    def test_upsert_new_document(self, tmp_path):
        """upsert() inserts a new document when _id does not exist."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.upsert({"_id": "u1", "name": "Alice"})
        assert doc_id == "u1"
        doc = table.get("u1")
        assert doc is not None
        assert doc["name"] == "Alice"

    def test_upsert_existing_document(self, tmp_path):
        """upsert() updates an existing document when _id exists."""
        table = Table(str(tmp_path / "t.json"))
        table.insert({"_id": "u1", "name": "Alice", "age": 30})
        doc_id = table.upsert({"_id": "u1", "name": "Alice Updated", "age": 31})
        assert doc_id == "u1"
        doc = table.get("u1")
        assert doc["name"] == "Alice Updated"
        assert doc["age"] == 31

    def test_upsert_without_id_inserts_new(self, tmp_path):
        """upsert() without _id always inserts with a generated ID."""
        table = Table(str(tmp_path / "t.json"))
        doc_id = table.upsert({"name": "Alice"})
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0
        doc = table.get(doc_id)
        assert doc is not None
        assert doc["name"] == "Alice"

    def test_upsert_returns_id(self, tmp_path):
        """upsert() returns the document's ID in all cases."""
        table = Table(str(tmp_path / "t.json"))
        id1 = table.upsert({"_id": "explicit", "name": "A"})
        id2 = table.upsert({"name": "B"})
        assert id1 == "explicit"
        assert isinstance(id2, str)

    def test_upsert_persists_to_disk(self, tmp_path):
        """Upserted document is persisted immediately."""
        path = str(tmp_path / "t.json")
        table = Table(path)
        doc_id = table.upsert({"_id": "u1", "name": "Alice"})
        # Re-open
        table2 = Table(path)
        doc = table2.get(doc_id)
        assert doc is not None
        assert doc["name"] == "Alice"
