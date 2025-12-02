"""Unit tests for FmtHandler."""

import json
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from contextgit.handlers.fmt_handler import FmtHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.domain.index.manager import IndexManager
from contextgit.models.node import Node
from contextgit.models.link import Link
from contextgit.models.index import Index
from contextgit.models.enums import NodeType, NodeStatus, RelationType, SyncStatus
from contextgit.models.location import HeadingLocation
from contextgit.exceptions import RepoNotFoundError, IndexCorruptedError
from contextgit.constants import CONTEXTGIT_DIR, INDEX_FILE


class TestFmtHandler:
    """Tests for FmtHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create FmtHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return FmtHandler(fs, yaml, formatter)

    @pytest.fixture
    def initialized_repo(self, temp_dir):
        """Create an initialized contextgit repository with unsorted index."""
        # Create .contextgit directory
        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        contextgit_dir.mkdir(parents=True, exist_ok=True)

        # Create config
        config_path = contextgit_dir / "config.yaml"
        config_path.write_text("tag_prefixes:\n  business: BR-\n")

        # Create an intentionally unsorted index
        # The fmt command should sort nodes by ID and links by (from_id, to_id)
        unsorted_index = {
            'nodes': [
                {
                    'id': 'SR-003',
                    'type': 'system',
                    'title': 'System requirement 3',
                    'file': 'docs/system.md',
                    'location': {'heading_path': ['Requirements']},
                    'status': 'draft',
                    'last_updated': '2024-01-01T00:00:00',
                    'checksum': 'hash3',
                    'tags': [],
                    'upstream': [],
                    'downstream': []
                },
                {
                    'id': 'SR-001',
                    'type': 'system',
                    'title': 'System requirement 1',
                    'file': 'docs/system.md',
                    'location': {'heading_path': ['Requirements']},
                    'status': 'draft',
                    'last_updated': '2024-01-01T00:00:00',
                    'checksum': 'hash1',
                    'tags': [],
                    'upstream': [],
                    'downstream': []
                },
                {
                    'id': 'SR-002',
                    'type': 'system',
                    'title': 'System requirement 2',
                    'file': 'docs/system.md',
                    'location': {'heading_path': ['Requirements']},
                    'status': 'draft',
                    'last_updated': '2024-01-01T00:00:00',
                    'checksum': 'hash2',
                    'tags': [],
                    'upstream': [],
                    'downstream': []
                }
            ],
            'links': [
                {
                    'from_id': 'SR-003',
                    'to_id': 'SR-001',
                    'relation_type': 'depends_on',
                    'sync_status': 'ok'
                },
                {
                    'from_id': 'SR-001',
                    'to_id': 'SR-002',
                    'relation_type': 'depends_on',
                    'sync_status': 'ok'
                },
                {
                    'from_id': 'SR-002',
                    'to_id': 'SR-003',
                    'relation_type': 'refines',
                    'sync_status': 'ok'
                }
            ]
        }

        # Write unsorted index
        yaml = YAMLSerializer()
        index_path = contextgit_dir / INDEX_FILE
        index_path.write_text(yaml.dump_yaml(unsorted_index))

        return temp_dir

    def test_fmt_formats_index_successfully(self, handler, initialized_repo, monkeypatch):
        """Test that fmt formats the index successfully."""
        # Change to the repo directory
        monkeypatch.chdir(initialized_repo)

        result = handler.handle(check=False, format="text")

        assert "Formatted .contextgit/requirements_index.yaml" in result
        assert "3 nodes" in result
        assert "3 links" in result

    def test_fmt_sorts_nodes_by_id(self, handler, initialized_repo, monkeypatch):
        """Test that fmt sorts nodes by ID."""
        monkeypatch.chdir(initialized_repo)

        # Format the index
        handler.handle(check=False, format="text")

        # Load the formatted index and verify sorting
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)
        index = index_mgr.load_index()

        node_ids = list(index.nodes.keys())
        assert node_ids == sorted(node_ids)
        assert node_ids == ['SR-001', 'SR-002', 'SR-003']

    def test_fmt_sorts_links_by_from_to(self, handler, initialized_repo, monkeypatch):
        """Test that fmt sorts links by (from_id, to_id)."""
        monkeypatch.chdir(initialized_repo)

        # Format the index
        handler.handle(check=False, format="text")

        # Load the formatted index and verify link sorting
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)
        index = index_mgr.load_index()

        link_tuples = [(link.from_id, link.to_id) for link in index.links]
        assert link_tuples == sorted(link_tuples)
        assert link_tuples == [
            ('SR-001', 'SR-002'),
            ('SR-002', 'SR-003'),
            ('SR-003', 'SR-001')
        ]

    def test_fmt_json_output(self, handler, initialized_repo, monkeypatch):
        """Test that fmt produces valid JSON output."""
        monkeypatch.chdir(initialized_repo)

        result = handler.handle(check=False, format="json")

        # Verify JSON is valid
        data = json.loads(result)
        assert data['status'] == 'success'
        assert data['message'] == 'Index formatted'
        assert data['node_count'] == 3
        assert data['link_count'] == 3

    def test_fmt_check_needs_formatting(self, handler, initialized_repo, monkeypatch):
        """Test that check mode detects when formatting is needed."""
        monkeypatch.chdir(initialized_repo)

        result = handler.handle(check=True, format="text")

        # Since the fixture creates an unsorted index, check should report it needs formatting
        assert "needs formatting" in result.lower()

    def test_fmt_check_already_formatted(self, handler, initialized_repo, monkeypatch):
        """Test that check mode detects when index is already formatted."""
        monkeypatch.chdir(initialized_repo)

        # First format the index
        handler.handle(check=False, format="text")

        # Now check should report it's already formatted
        result = handler.handle(check=True, format="text")
        assert "already formatted" in result.lower()

    def test_fmt_check_json_output(self, handler, initialized_repo, monkeypatch):
        """Test that check mode produces valid JSON output."""
        monkeypatch.chdir(initialized_repo)

        result = handler.handle(check=True, format="json")

        # Verify JSON is valid
        data = json.loads(result)
        assert 'needs_formatting' in data
        assert 'node_count' in data
        assert 'link_count' in data
        assert data['node_count'] == 3
        assert data['link_count'] == 3

    def test_fmt_with_empty_index(self, handler, temp_dir, monkeypatch):
        """Test that fmt works with an empty index."""
        # Create .contextgit directory
        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        contextgit_dir.mkdir(parents=True, exist_ok=True)

        # Create empty index
        yaml = YAMLSerializer()
        index_path = contextgit_dir / INDEX_FILE
        empty_index = {'nodes': [], 'links': []}
        index_path.write_text(yaml.dump_yaml(empty_index))

        monkeypatch.chdir(temp_dir)

        result = handler.handle(check=False, format="text")

        assert "Formatted .contextgit/requirements_index.yaml" in result
        assert "0 nodes" in result
        assert "0 links" in result

    def test_fmt_raises_error_outside_repo(self, handler, temp_dir, monkeypatch):
        """Test that fmt raises error when not in a contextgit repository."""
        # Don't create .contextgit directory
        monkeypatch.chdir(temp_dir)

        with pytest.raises(FileNotFoundError, match="Not in a contextgit repository"):
            handler.handle(check=False, format="text")

    def test_fmt_preserves_data_integrity(self, handler, initialized_repo, monkeypatch):
        """Test that fmt preserves all data while formatting."""
        monkeypatch.chdir(initialized_repo)

        # Load original index
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)
        original_index = index_mgr.load_index()

        # Format the index
        handler.handle(check=False, format="text")

        # Load formatted index
        formatted_index = index_mgr.load_index()

        # Verify all nodes are preserved
        assert len(original_index.nodes) == len(formatted_index.nodes)
        for node_id in original_index.nodes:
            assert node_id in formatted_index.nodes
            orig_node = original_index.nodes[node_id]
            fmt_node = formatted_index.nodes[node_id]
            assert orig_node.id == fmt_node.id
            assert orig_node.title == fmt_node.title
            assert orig_node.type == fmt_node.type

        # Verify all links are preserved
        assert len(original_index.links) == len(formatted_index.links)
        orig_link_tuples = {(l.from_id, l.to_id) for l in original_index.links}
        fmt_link_tuples = {(l.from_id, l.to_id) for l in formatted_index.links}
        assert orig_link_tuples == fmt_link_tuples
