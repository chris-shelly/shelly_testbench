"""US-012: Query engine -- logical combinators tests."""

from smalldoc_db.query import matches


class TestLogicalAnd:
    """Tests for $and combinator."""

    def test_and_all_match(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$and": [{"name": "Alice"}, {"age": 30}]}
        assert matches(doc, filt) is True

    def test_and_one_fails(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$and": [{"name": "Alice"}, {"age": 99}]}
        assert matches(doc, filt) is False

    def test_and_all_fail(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$and": [{"name": "Bob"}, {"age": 99}]}
        assert matches(doc, filt) is False


class TestLogicalOr:
    """Tests for $or combinator."""

    def test_or_one_matches(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$or": [{"name": "Bob"}, {"age": 30}]}
        assert matches(doc, filt) is True

    def test_or_all_match(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$or": [{"name": "Alice"}, {"age": 30}]}
        assert matches(doc, filt) is True

    def test_or_none_match(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$or": [{"name": "Bob"}, {"age": 99}]}
        assert matches(doc, filt) is False


class TestLogicalNot:
    """Tests for $not combinator."""

    def test_not_inverts_match(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$not": {"name": "Bob"}}
        assert matches(doc, filt) is True

    def test_not_inverts_non_match(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$not": {"name": "Alice"}}
        assert matches(doc, filt) is False


class TestLogicalNested:
    """Tests for nested logical + comparison operator combinations."""

    def test_and_with_comparison_operators(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$and": [{"name": "Alice"}, {"age": {"$gte": 18}}]}
        assert matches(doc, filt) is True

    def test_or_with_comparison_operators(self):
        doc = {"name": "Alice", "age": 30}
        filt = {"$or": [{"age": {"$lt": 10}}, {"age": {"$gt": 25}}]}
        assert matches(doc, filt) is True

    def test_not_with_comparison_operator(self):
        doc = {"age": 30}
        filt = {"$not": {"age": {"$lt": 18}}}
        assert matches(doc, filt) is True

    def test_deeply_nested_combination(self):
        """Complex nested query: ($or with $and and $not inside)."""
        doc = {"name": "Alice", "age": 30, "city": "NYC"}
        filt = {
            "$or": [
                {"$and": [{"name": "Alice"}, {"age": {"$gte": 21}}]},
                {"$not": {"city": "NYC"}},
            ]
        }
        assert matches(doc, filt) is True

    def test_deeply_nested_no_match(self):
        doc = {"name": "Bob", "age": 15, "city": "NYC"}
        filt = {
            "$or": [
                {"$and": [{"name": "Alice"}, {"age": {"$gte": 21}}]},
                {"$not": {"city": "NYC"}},
            ]
        }
        assert matches(doc, filt) is False
