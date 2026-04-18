"""US-010: Query engine -- equality matching tests."""

from smalldoc_db.query import matches


class TestMatchesEquality:
    """Tests for the matches() function with equality filters."""

    def test_empty_filter_matches_everything(self):
        """Empty filter {} matches any document."""
        assert matches({"name": "Alice", "age": 30}, {}) is True
        assert matches({}, {}) is True

    def test_single_equality_match(self):
        """Single-key equality filter matches when value equals."""
        assert matches({"name": "Alice", "age": 30}, {"name": "Alice"}) is True

    def test_single_equality_no_match(self):
        """Single-key equality filter does not match different value."""
        assert matches({"name": "Alice"}, {"name": "Bob"}) is False

    def test_multi_key_equality_all_match(self):
        """Multiple keys in filter act as implicit AND -- all must match."""
        doc = {"name": "Alice", "age": 30, "city": "NYC"}
        assert matches(doc, {"name": "Alice", "age": 30}) is True

    def test_multi_key_equality_partial_match(self):
        """Multiple keys in filter fail if any key does not match."""
        doc = {"name": "Alice", "age": 30}
        assert matches(doc, {"name": "Alice", "age": 99}) is False

    def test_missing_field_does_not_match(self):
        """Filter on a field not present in the document does not match."""
        assert matches({"name": "Alice"}, {"age": 30}) is False

    def test_equality_with_various_types(self):
        """Equality works with int, float, bool, and None values."""
        doc = {"a": 1, "b": 2.5, "c": True, "d": None}
        assert matches(doc, {"a": 1}) is True
        assert matches(doc, {"b": 2.5}) is True
        assert matches(doc, {"c": True}) is True
        assert matches(doc, {"d": None}) is True
