"""US-011: Query engine -- comparison operators tests."""

import pytest

from smalldoc_db.query import matches


class TestComparisonEq:
    """Tests for $eq operator."""

    def test_eq_match(self):
        assert matches({"age": 30}, {"age": {"$eq": 30}}) is True

    def test_eq_no_match(self):
        assert matches({"age": 30}, {"age": {"$eq": 31}}) is False


class TestComparisonNe:
    """Tests for $ne operator."""

    def test_ne_match(self):
        assert matches({"age": 30}, {"age": {"$ne": 31}}) is True

    def test_ne_no_match(self):
        assert matches({"age": 30}, {"age": {"$ne": 30}}) is False


class TestComparisonGt:
    """Tests for $gt operator."""

    def test_gt_match(self):
        assert matches({"age": 30}, {"age": {"$gt": 20}}) is True

    def test_gt_equal_no_match(self):
        assert matches({"age": 30}, {"age": {"$gt": 30}}) is False

    def test_gt_less_no_match(self):
        assert matches({"age": 30}, {"age": {"$gt": 40}}) is False


class TestComparisonGte:
    """Tests for $gte operator."""

    def test_gte_greater(self):
        assert matches({"age": 30}, {"age": {"$gte": 20}}) is True

    def test_gte_equal(self):
        assert matches({"age": 30}, {"age": {"$gte": 30}}) is True

    def test_gte_less_no_match(self):
        assert matches({"age": 30}, {"age": {"$gte": 40}}) is False


class TestComparisonLt:
    """Tests for $lt operator."""

    def test_lt_match(self):
        assert matches({"age": 30}, {"age": {"$lt": 40}}) is True

    def test_lt_equal_no_match(self):
        assert matches({"age": 30}, {"age": {"$lt": 30}}) is False

    def test_lt_greater_no_match(self):
        assert matches({"age": 30}, {"age": {"$lt": 20}}) is False


class TestComparisonLte:
    """Tests for $lte operator."""

    def test_lte_less(self):
        assert matches({"age": 30}, {"age": {"$lte": 40}}) is True

    def test_lte_equal(self):
        assert matches({"age": 30}, {"age": {"$lte": 30}}) is True

    def test_lte_greater_no_match(self):
        assert matches({"age": 30}, {"age": {"$lte": 20}}) is False


class TestComparisonIn:
    """Tests for $in operator."""

    def test_in_match(self):
        assert matches({"status": "active"}, {"status": {"$in": ["active", "pending"]}}) is True

    def test_in_no_match(self):
        assert matches({"status": "deleted"}, {"status": {"$in": ["active", "pending"]}}) is False


class TestComparisonNin:
    """Tests for $nin operator."""

    def test_nin_match(self):
        assert matches({"status": "deleted"}, {"status": {"$nin": ["active", "pending"]}}) is True

    def test_nin_no_match(self):
        assert matches({"status": "active"}, {"status": {"$nin": ["active", "pending"]}}) is False


class TestUnknownOperator:
    """Tests for unknown operators."""

    def test_unknown_operator_raises_value_error(self):
        with pytest.raises(ValueError):
            matches({"age": 30}, {"age": {"$unknown": 5}})
