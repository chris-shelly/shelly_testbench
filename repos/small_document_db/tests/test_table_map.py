"""US-014: Table.map() bulk transformation tests."""

from smalldoc_db.table import Table


class TestTableMap:
    """Tests for Table.map()."""

    def _seed_table(self, tmp_path):
        """Helper: creates a table with sample data and returns (table, ids)."""
        table = Table(str(tmp_path / "t.json"))
        ids = []
        ids.append(table.insert({"name": "Alice", "age": 30, "city": "NYC"}))
        ids.append(table.insert({"name": "Bob", "age": 25, "city": "LA"}))
        ids.append(table.insert({"name": "Charlie", "age": 35, "city": "NYC"}))
        return table, ids

    def test_map_over_all(self, tmp_path):
        """map() with empty filter transforms all documents."""
        table, ids = self._seed_table(tmp_path)
        count = table.map({}, lambda doc: {**doc, "processed": True})
        assert count == 3
        for doc_id in ids:
            doc = table.get(doc_id)
            assert doc["processed"] is True

    def test_map_over_filtered_subset(self, tmp_path):
        """map() only transforms documents matching the filter."""
        table, ids = self._seed_table(tmp_path)
        count = table.map({"city": "NYC"}, lambda doc: {**doc, "tagged": True})
        assert count == 2
        # NYC docs should have the tag
        alice = table.get(ids[0])
        assert alice["tagged"] is True
        charlie = table.get(ids[2])
        assert charlie["tagged"] is True
        # LA doc should not
        bob = table.get(ids[1])
        assert "tagged" not in bob

    def test_map_adds_field(self, tmp_path):
        """map() can add new fields to documents."""
        table, ids = self._seed_table(tmp_path)
        table.map({}, lambda doc: {**doc, "new_field": "hello"})
        for doc_id in ids:
            doc = table.get(doc_id)
            assert doc["new_field"] == "hello"

    def test_map_returns_count(self, tmp_path):
        """map() returns the number of documents transformed."""
        table, ids = self._seed_table(tmp_path)
        count = table.map({"name": "Alice"}, lambda doc: {**doc, "x": 1})
        assert count == 1
        count_all = table.map({}, lambda doc: {**doc, "y": 2})
        assert count_all == 3

    def test_map_preserves_id(self, tmp_path):
        """map() preserves the _id of each document even if fn omits it."""
        table, ids = self._seed_table(tmp_path)
        # fn returns a dict without _id -- map should preserve it
        table.map({}, lambda doc: {"name": doc["name"].upper()})
        for doc_id in ids:
            doc = table.get(doc_id)
            assert doc["_id"] == doc_id

    def test_map_persists_to_disk(self, tmp_path):
        """map() changes are persisted and survive re-loading."""
        path = str(tmp_path / "t.json")
        table = Table(path)
        doc_id = table.insert({"name": "Alice", "age": 30})
        table.map({}, lambda doc: {**doc, "age": doc["age"] + 1})
        # Re-open
        table2 = Table(path)
        doc = table2.get(doc_id)
        assert doc["age"] == 31

    def test_map_no_matches(self, tmp_path):
        """map() with no matching documents returns 0 and changes nothing."""
        table, ids = self._seed_table(tmp_path)
        count = table.map({"name": "Nonexistent"}, lambda doc: {**doc, "x": 1})
        assert count == 0
