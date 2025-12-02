"""Unit tests for ShowHandler."""

import json
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from contextgit.handlers.show_handler import ShowHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.domain.index.manager import IndexManager
from contextgit.models.node import Node
from contextgit.models.link import Link
from contextgit.models.index import Index
from contextgit.models.enums import NodeType, NodeStatus, RelationType, SyncStatus
from contextgit.models.location import HeadingLocation
from contextgit.exceptions import NodeNotFoundError, RepoNotFoundError
from contextgit.constants import CONTEXTGIT_DIR, INDEX_FILE


class TestShowHandler:
    """Tests for ShowHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create ShowHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return ShowHandler(fs, yaml, formatter)

    @pytest.fixture
    def initialized_repo(self, temp_dir):
        """Create an initialized contextgit repository."""
        # Create .contextgit directory
        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        contextgit_dir.mkdir(parents=True, exist_ok=True)

        # Create empty config (not needed for show tests)
        config_path = contextgit_dir / "config.yaml"
        config_path.write_text("tag_prefixes:\n  business: BR-\n")

        return temp_dir

    @pytest.fixture
    def sample_index(self, initialized_repo):
        """Create a sample index with nodes and links."""
        fs = FileSystem()
        yaml = YAMLSerializer()

        # Create sample nodes
        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Scheduled jobs must be observable",
            file="docs/requirements.md",
            location=HeadingLocation(path=["Business Requirements", "Observability"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=["feature:observability"]
        )

        node2 = Node(
            id="SR-010",
            type=NodeType.SYSTEM,
            title="System shall expose job execution logs via API",
            file="docs/02_system/logging_api.md",
            location=HeadingLocation(path=["System Design - Logging", "3.1 Logging API"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
            llm_generated=False,
            tags=["feature:observability", "api:rest"]
        )

        node3 = Node(
            id="AR-020",
            type=NodeType.ARCHITECTURE,
            title="REST API design for logging",
            file="docs/03_architecture/api_design.md",
            location=HeadingLocation(path=["API Design", "Logging Endpoints"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="c" * 64,
            llm_generated=True,
            tags=["api:rest"]
        )

        node4 = Node(
            id="C-120",
            type=NodeType.CODE,
            title="LoggingAPIHandler class",
            file="src/api/logging.py",
            location=HeadingLocation(path=["LoggingAPIHandler"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="d" * 64,
            llm_generated=False,
            tags=[]
        )

        # Create links
        link1 = Link(
            from_id="BR-001",
            to_id="SR-010",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        link2 = Link(
            from_id="SR-010",
            to_id="AR-020",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        link3 = Link(
            from_id="SR-010",
            to_id="C-120",
            relation_type=RelationType.IMPLEMENTS,
            sync_status=SyncStatus.UPSTREAM_CHANGED,
            last_checked="2025-12-02T18:00:00Z"
        )

        # Create index
        index = Index()
        index.nodes = {
            "BR-001": node1,
            "SR-010": node2,
            "AR-020": node3,
            "C-120": node4,
        }
        index.links = [link1, link2, link3]

        # Save index
        index_mgr = IndexManager(fs, yaml, initialized_repo)
        index_mgr.save_index(index)

        return initialized_repo

    def test_show_displays_node_details_text_format(self, handler, sample_index, monkeypatch):
        """Test that show displays node details in text format."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(node_id="SR-010", format="text")

        # Check basic node information
        assert "Node: SR-010" in result
        assert "Type: system" in result
        assert "Title: System shall expose job execution logs via API" in result
        assert "File: docs/02_system/logging_api.md" in result
        assert "Status: active" in result
        assert "Checksum: " + ("b" * 64) in result
        assert "Tags: feature:observability, api:rest" in result

        # Check upstream links
        assert "Upstream (1):" in result
        assert "BR-001" in result
        assert "Scheduled jobs must be observable" in result
        assert "[refines]" in result
        assert "(ok)" in result

        # Check downstream links
        assert "Downstream (2):" in result
        assert "AR-020" in result
        assert "REST API design for logging" in result
        assert "C-120" in result
        assert "LoggingAPIHandler class" in result
        assert "[implements]" in result
        assert "(upstream_changed)" in result

    def test_show_displays_node_details_json_format(self, handler, sample_index, monkeypatch):
        """Test that show displays node details in JSON format."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(node_id="SR-010", format="json")

        # Parse JSON
        data = json.loads(result)

        # Check node data
        assert data["node"]["id"] == "SR-010"
        assert data["node"]["type"] == "system"
        assert data["node"]["title"] == "System shall expose job execution logs via API"
        assert data["node"]["file"] == "docs/02_system/logging_api.md"
        assert data["node"]["status"] == "active"
        assert data["node"]["checksum"] == "b" * 64
        assert data["node"]["tags"] == ["api:rest", "feature:observability"]  # Sorted

        # Check upstream links
        assert len(data["upstream"]) == 1
        assert data["upstream"][0]["id"] == "BR-001"
        assert data["upstream"][0]["title"] == "Scheduled jobs must be observable"
        assert data["upstream"][0]["relation"] == "refines"
        assert data["upstream"][0]["sync_status"] == "ok"

        # Check downstream links
        assert len(data["downstream"]) == 2
        downstream_ids = [link["id"] for link in data["downstream"]]
        assert "AR-020" in downstream_ids
        assert "C-120" in downstream_ids

        # Check specific downstream link
        c120_link = next(link for link in data["downstream"] if link["id"] == "C-120")
        assert c120_link["title"] == "LoggingAPIHandler class"
        assert c120_link["relation"] == "implements"
        assert c120_link["sync_status"] == "upstream_changed"

    def test_show_node_with_no_links(self, handler, initialized_repo, monkeypatch):
        """Test showing a node with no upstream or downstream links."""
        monkeypatch.chdir(initialized_repo)

        # Create isolated node
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        index = Index()
        node = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Standalone requirement",
            file="docs/requirements.md",
            location=HeadingLocation(path=["Requirements"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )
        index.nodes = {"BR-001": node}
        index_mgr.save_index(index)

        result = handler.handle(node_id="BR-001", format="text")

        # Should show node details but no link sections
        assert "Node: BR-001" in result
        assert "Upstream" not in result
        assert "Downstream" not in result

    def test_show_raises_error_for_nonexistent_node(self, handler, sample_index, monkeypatch):
        """Test that show raises NodeNotFoundError for nonexistent node."""
        monkeypatch.chdir(sample_index)

        with pytest.raises(NodeNotFoundError) as exc_info:
            handler.handle(node_id="SR-999", format="text")

        assert "SR-999" in str(exc_info.value)

    def test_show_raises_error_when_not_in_repo(self, handler, temp_dir, monkeypatch):
        """Test that show raises RepoNotFoundError when not in a contextgit repo."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(RepoNotFoundError) as exc_info:
            handler.handle(node_id="SR-010", format="text")

        assert "Not in a contextgit repository" in str(exc_info.value)

    def test_show_formats_location_heading(self, handler, sample_index, monkeypatch):
        """Test that show formats heading locations correctly."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(node_id="SR-010", format="text")

        # Check location format with arrow
        assert 'Location: heading → ["System Design - Logging", "3.1 Logging API"]' in result

    def test_show_json_structure_complete(self, handler, sample_index, monkeypatch):
        """Test that JSON output has all required fields."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(node_id="SR-010", format="json")
        data = json.loads(result)

        # Check structure
        assert "node" in data
        assert "upstream" in data
        assert "downstream" in data

        # Check node has all fields
        node = data["node"]
        required_fields = ["id", "type", "title", "file", "location", "status",
                          "last_updated", "checksum", "llm_generated", "tags"]
        for field in required_fields:
            assert field in node, f"Missing field: {field}"

    def test_show_displays_multiple_upstream_links(self, handler, initialized_repo, monkeypatch):
        """Test showing a node with multiple upstream links."""
        monkeypatch.chdir(initialized_repo)

        # Create nodes with multiple upstream links
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Business Req 1",
            file="docs/business.md",
            location=HeadingLocation(path=["Req1"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )

        node2 = Node(
            id="BR-002",
            type=NodeType.BUSINESS,
            title="Business Req 2",
            file="docs/business.md",
            location=HeadingLocation(path=["Req2"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
            llm_generated=False,
            tags=[]
        )

        node3 = Node(
            id="SR-001",
            type=NodeType.SYSTEM,
            title="System Requirement",
            file="docs/system.md",
            location=HeadingLocation(path=["SysReq"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="c" * 64,
            llm_generated=False,
            tags=[]
        )

        link1 = Link(
            from_id="BR-001",
            to_id="SR-001",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        link2 = Link(
            from_id="BR-002",
            to_id="SR-001",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        index = Index()
        index.nodes = {"BR-001": node1, "BR-002": node2, "SR-001": node3}
        index.links = [link1, link2]
        index_mgr.save_index(index)

        result = handler.handle(node_id="SR-001", format="text")

        # Should show both upstream links
        assert "Upstream (2):" in result
        assert "BR-001" in result
        assert "BR-002" in result
        assert "Business Req 1" in result
        assert "Business Req 2" in result

    def test_show_node_with_empty_tags(self, handler, sample_index, monkeypatch):
        """Test showing a node with no tags doesn't display Tags line."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(node_id="C-120", format="text")

        # C-120 has no tags, so Tags line should not appear
        assert "Node: C-120" in result
        lines = result.split('\n')
        tag_lines = [line for line in lines if line.startswith("Tags:")]
        assert len(tag_lines) == 0
