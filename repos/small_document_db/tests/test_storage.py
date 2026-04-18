"""US-003: Table JSON persistence primitives tests."""

import json
import os

from smalldoc_db.storage import load_table, save_table


class TestLoadTable:
    """Tests for the load_table() function."""

    def test_load_missing_file_returns_empty_dict(self, tmp_path):
        """load_table returns {} when the file does not exist."""
        path = tmp_path / "nonexistent.json"
        result = load_table(str(path))
        assert result == {}

    def test_load_existing_file(self, tmp_path):
        """load_table reads back a previously written JSON file."""
        path = tmp_path / "data.json"
        data = {"id1": {"name": "Alice"}, "id2": {"name": "Bob"}}
        path.write_text(json.dumps(data))
        result = load_table(str(path))
        assert result == data


class TestSaveTable:
    """Tests for the save_table() function."""

    def test_save_creates_file(self, tmp_path):
        """save_table creates a new JSON file."""
        path = tmp_path / "data.json"
        docs = {"id1": {"name": "Alice"}}
        save_table(str(path), docs)
        assert path.exists()

    def test_save_then_load_round_trip(self, tmp_path):
        """Data survives a save -> load round trip."""
        path = tmp_path / "data.json"
        docs = {"id1": {"name": "Alice", "age": 30}, "id2": {"name": "Bob", "age": 25}}
        save_table(str(path), docs)
        result = load_table(str(path))
        assert result == docs

    def test_save_overwrites_existing(self, tmp_path):
        """save_table overwrites previous contents."""
        path = tmp_path / "data.json"
        save_table(str(path), {"id1": {"name": "Alice"}})
        save_table(str(path), {"id2": {"name": "Bob"}})
        result = load_table(str(path))
        assert result == {"id2": {"name": "Bob"}}
        assert "id1" not in result

    def test_save_writes_valid_json(self, tmp_path):
        """Saved file is valid JSON."""
        path = tmp_path / "data.json"
        docs = {"id1": {"x": 1}}
        save_table(str(path), docs)
        with open(str(path)) as f:
            parsed = json.load(f)
        assert parsed == docs

    def test_save_atomic_no_partial_write(self, tmp_path):
        """After save_table completes, the file contains the full data (not partial)."""
        path = tmp_path / "data.json"
        docs = {f"id{i}": {"val": i} for i in range(100)}
        save_table(str(path), docs)
        result = load_table(str(path))
        assert len(result) == 100
