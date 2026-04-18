"""US-013: Table.find() integrated with query engine tests."""

from smalldoc_db.table import Table


class TestTableFind:
    """Tests for Table.find()."""

    def _seed_table(self, tmp_path):
        """Helper: creates a table with sample data and returns (table, ids)."""
        table = Table(str(tmp_path / "t.json"))
        ids = []
        ids.append(table.insert({"name": "Alice", "age": 30, "city": "NYC"}))
        ids.append(table.insert({"name": "Bob", "age": 25, "city": "LA"}))
        ids.append(table.insert({"name": "Charlie", "age": 35, "city": "NYC"}))
        ids.append(table.insert({"name": "Diana", "age": 20, "city": "Chicago"}))
        return table, ids

    def test_find_all_with_none(self, tmp_path):
        """find(None) returns all documents."""
        table, ids = self._seed_table(tmp_path)
        results = table.find(None)
        assert len(results) == 4

    def test_find_all_with_empty_filter(self, tmp_path):
        """find({}) returns all documents."""
        table, ids = self._seed_table(tmp_path)
        results = table.find({})
        assert len(results) == 4

    def test_find_with_equality_filter(self, tmp_path):
        """find() with equality filter returns matching documents."""
        table, ids = self._seed_table(tmp_path)
        results = table.find({"city": "NYC"})
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert names == {"Alice", "Charlie"}

    def test_find_with_gt_operator(self, tmp_path):
        """find() with $gt operator returns matching documents."""
        table, ids = self._seed_table(tmp_path)
        results = table.find({"age": {"$gt": 28}})
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert names == {"Alice", "Charlie"}

    def test_find_with_or_operator(self, tmp_path):
        """find() with $or operator returns matching documents."""
        table, ids = self._seed_table(tmp_path)
        results = table.find({"$or": [{"name": "Alice"}, {"name": "Diana"}]})
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert names == {"Alice", "Diana"}

    def test_find_no_matches(self, tmp_path):
        """find() returns empty list when nothing matches."""
        table, ids = self._seed_table(tmp_path)
        results = table.find({"name": "Nonexistent"})
        assert results == []

    def test_find_results_include_id(self, tmp_path):
        """Each returned document includes its _id field."""
        table, ids = self._seed_table(tmp_path)
        results = table.find({})
        for doc in results:
            assert "_id" in doc

    def test_find_returns_copies(self, tmp_path):
        """Mutating returned documents does not affect stored data."""
        table, ids = self._seed_table(tmp_path)
        results = table.find({"name": "Alice"})
        results[0]["name"] = "MODIFIED"
        # Re-find should still have original
        results2 = table.find({"name": "Alice"})
        assert len(results2) == 1
        assert results2[0]["name"] == "Alice"

    def test_find_on_empty_table(self, tmp_path):
        """find() on empty table returns empty list."""
        table = Table(str(tmp_path / "t.json"))
        assert table.find({}) == []
        assert table.find(None) == []
