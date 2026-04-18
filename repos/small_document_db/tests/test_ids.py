"""US-002: Document ID generation utility tests."""

from smalldoc_db.ids import generate_id


class TestGenerateId:
    """Tests for the generate_id() function."""

    def test_returns_string(self):
        """generate_id() returns a str."""
        result = generate_id()
        assert isinstance(result, str)

    def test_two_calls_return_different_ids(self):
        """Two consecutive calls produce different IDs."""
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2

    def test_id_is_nonempty(self):
        """Generated ID is not an empty string."""
        result = generate_id()
        assert len(result) > 0

    def test_many_ids_are_unique(self):
        """A batch of generated IDs contains no duplicates."""
        ids = [generate_id() for _ in range(1000)]
        assert len(set(ids)) == 1000
