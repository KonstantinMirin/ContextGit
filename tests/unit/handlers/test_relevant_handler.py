"""Unit tests for RelevantHandler."""

import json
import tempfile
from pathlib import Path
import pytest

from contextgit.handlers.relevant_handler import RelevantHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.domain.index.manager import IndexManager
from contextgit.models.node import Node
from contextgit.models.link import Link
from contextgit.models.index import Index
from contextgit.models.enums import NodeType, NodeStatus, RelationType, SyncStatus
from contextgit.models.location import HeadingLocation
from contextgit.exceptions import RepoNotFoundError
from contextgit.constants import CONTEXTGIT_DIR, INDEX_FILE


class TestRelevantHandler:
    """Tests for RelevantHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create RelevantHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return RelevantHandler(fs, yaml, formatter)

    @pytest.fixture
    def initialized_repo(self, temp_dir):
        """Create an initialized contextgit repository."""
        # Create .contextgit directory
        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        contextgit_dir.mkdir(parents=True, exist_ok=True)

        # Create empty config
        config_path = contextgit_dir / "config.yaml"
        config_path.write_text("tag_prefixes:\n  business: BR-\n")

        return temp_dir

    @pytest.fixture
    def sample_index_with_code(self, initialized_repo):
        """Create a sample index with full traceability chain ending in code."""
        fs = FileSystem()
        yaml = YAMLSerializer()

        # Create nodes representing full traceability chain
        # BR-001 -> SR-010 -> AR-020 -> C-120
        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Scheduled jobs must be observable",
            file="docs/requirements.md",
            location=HeadingLocation(path=["Business Requirements"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
        )

        node2 = Node(
            id="SR-010",
            type=NodeType.SYSTEM,
            title="System shall expose job execution logs via API",
            file="docs/02_system/logging_api.md",
            location=HeadingLocation(path=["System Design"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
        )

        node3 = Node(
            id="AR-020",
            type=NodeType.ARCHITECTURE,
            title="REST API design for logging",
            file="docs/03_architecture/api_design.md",
            location=HeadingLocation(path=["API Design"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="c" * 64,
        )

        node4 = Node(
            id="C-120",
            type=NodeType.CODE,
            title="LoggingAPIHandler class",
            file="src/logging/api.py",
            location=HeadingLocation(path=["Implementation"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="d" * 64,
        )

        # Create links forming the chain
        link1 = Link(
            from_id="BR-001",
            to_id="SR-010",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z",
        )

        link2 = Link(
            from_id="SR-010",
            to_id="AR-020",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z",
        )

        link3 = Link(
            from_id="AR-020",
            to_id="C-120",
            relation_type=RelationType.IMPLEMENTS,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z",
        )

        # Create index
        index = Index(
            nodes={
                "BR-001": node1,
                "SR-010": node2,
                "AR-020": node3,
                "C-120": node4,
            },
            links=[link1, link2, link3]
        )

        # Save index
        index_mgr = IndexManager(fs, yaml, initialized_repo)
        index_mgr.save_index(index)

        return initialized_repo

    def test_find_relevant_for_file_with_matches(
        self, handler, sample_index_with_code, monkeypatch
    ):
        """Test finding relevant requirements for a file that has matches."""
        # Change to the test repo directory
        monkeypatch.chdir(sample_index_with_code)

        # Test with default depth (should find all 4 nodes)
        result = handler.handle(
            file_path="src/logging/api.py",
            depth=3,
            format="text"
        )

        # Verify output contains all nodes
        assert "Requirements relevant to src/logging/api.py:" in result
        assert "C-120" in result
        assert "AR-020" in result
        assert "SR-010" in result
        assert "BR-001" in result

    def test_find_relevant_for_file_with_depth_limit(
        self, handler, sample_index_with_code, monkeypatch
    ):
        """Test that depth limit works correctly."""
        monkeypatch.chdir(sample_index_with_code)

        # Depth 1 should find C-120 (distance 0) and AR-020 (distance 1)
        result = handler.handle(
            file_path="src/logging/api.py",
            depth=1,
            format="text"
        )

        assert "C-120" in result
        assert "AR-020" in result
        assert "SR-010" not in result
        assert "BR-001" not in result

    def test_find_relevant_for_file_json_format(
        self, handler, sample_index_with_code, monkeypatch
    ):
        """Test JSON output format."""
        monkeypatch.chdir(sample_index_with_code)

        result = handler.handle(
            file_path="src/logging/api.py",
            depth=3,
            format="json"
        )

        data = json.loads(result)

        # Check structure
        assert "file" in data
        assert "nodes" in data
        assert data["file"] == "src/logging/api.py"

        # Check nodes are sorted by distance
        nodes = data["nodes"]
        assert len(nodes) == 4

        # First node should be the code node (distance 0)
        assert nodes[0]["id"] == "C-120"
        assert nodes[0]["distance"] == 0
        assert nodes[0]["type"] == "code"

        # Check all nodes have required fields
        for node in nodes:
            assert "id" in node
            assert "type" in node
            assert "title" in node
            assert "file" in node
            assert "distance" in node

        # Verify distances are correct
        distances = {node["id"]: node["distance"] for node in nodes}
        assert distances["C-120"] == 0
        assert distances["AR-020"] == 1
        assert distances["SR-010"] == 2
        assert distances["BR-001"] == 3

    def test_find_relevant_for_file_no_matches(
        self, handler, sample_index_with_code, monkeypatch
    ):
        """Test with a file that has no nodes."""
        monkeypatch.chdir(sample_index_with_code)

        result = handler.handle(
            file_path="src/unknown/file.py",
            depth=3,
            format="text"
        )

        assert "No requirements found" in result
        assert "src/unknown/file.py" in result

    def test_find_relevant_for_file_no_matches_json(
        self, handler, sample_index_with_code, monkeypatch
    ):
        """Test JSON format when no nodes found."""
        monkeypatch.chdir(sample_index_with_code)

        result = handler.handle(
            file_path="src/unknown/file.py",
            depth=3,
            format="json"
        )

        data = json.loads(result)
        assert data["file"] == "src/unknown/file.py"
        assert data["nodes"] == []

    def test_not_in_repo(self, handler, temp_dir, monkeypatch):
        """Test error when not in a contextgit repository."""
        # Use a temp dir without .contextgit
        monkeypatch.chdir(temp_dir)

        with pytest.raises(RepoNotFoundError):
            handler.handle(
                file_path="src/test.py",
                depth=3,
                format="text"
            )

    def test_text_format_grouping(
        self, handler, sample_index_with_code, monkeypatch
    ):
        """Test that text output groups nodes by distance."""
        monkeypatch.chdir(sample_index_with_code)

        result = handler.handle(
            file_path="src/logging/api.py",
            depth=3,
            format="text"
        )

        # Check grouping headers
        assert "Direct:" in result
        assert "Upstream (1 level):" in result
        assert "Upstream (2 levels):" in result
        assert "Upstream (3 levels):" in result

        # Verify structure - Direct should come before Upstream
        lines = result.split('\n')
        direct_idx = None
        upstream_1_idx = None
        upstream_2_idx = None
        upstream_3_idx = None

        for i, line in enumerate(lines):
            if "Direct:" in line:
                direct_idx = i
            elif "Upstream (1 level):" in line:
                upstream_1_idx = i
            elif "Upstream (2 levels):" in line:
                upstream_2_idx = i
            elif "Upstream (3 levels):" in line:
                upstream_3_idx = i

        # Verify order
        assert direct_idx is not None
        assert upstream_1_idx is not None
        assert upstream_2_idx is not None
        assert upstream_3_idx is not None
        assert direct_idx < upstream_1_idx < upstream_2_idx < upstream_3_idx

    def test_absolute_path_normalization(
        self, handler, sample_index_with_code, monkeypatch
    ):
        """Test that absolute paths are normalized to relative."""
        monkeypatch.chdir(sample_index_with_code)

        abs_path = Path(sample_index_with_code) / "src/logging/api.py"
        result = handler.handle(
            file_path=str(abs_path),
            depth=3,
            format="json"
        )

        data = json.loads(result)
        # Should normalize to relative path
        assert data["file"] == "src/logging/api.py"
        assert len(data["nodes"]) == 4

    def test_multiple_nodes_same_file(self, initialized_repo, handler, monkeypatch):
        """Test when multiple nodes reference the same file."""
        fs = FileSystem()
        yaml = YAMLSerializer()

        # Create two nodes for the same file, plus upstream
        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Business requirement",
            file="docs/req.md",
            location=HeadingLocation(path=["Requirements"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
        )

        node2 = Node(
            id="C-100",
            type=NodeType.CODE,
            title="Function A",
            file="src/code.py",
            location=HeadingLocation(path=["Functions"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
        )

        node3 = Node(
            id="C-101",
            type=NodeType.CODE,
            title="Function B",
            file="src/code.py",  # Same file
            location=HeadingLocation(path=["Functions"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="c" * 64,
        )

        # Both code nodes link to same upstream
        link1 = Link(
            from_id="BR-001",
            to_id="C-100",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z",
        )

        link2 = Link(
            from_id="BR-001",
            to_id="C-101",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z",
        )

        index = Index(
            nodes={
                "BR-001": node1,
                "C-100": node2,
                "C-101": node3,
            },
            links=[link1, link2]
        )

        index_mgr = IndexManager(fs, yaml, initialized_repo)
        index_mgr.save_index(index)

        monkeypatch.chdir(initialized_repo)

        result = handler.handle(
            file_path="src/code.py",
            depth=3,
            format="json"
        )

        data = json.loads(result)

        # Should find both code nodes and the shared upstream
        node_ids = {node["id"] for node in data["nodes"]}
        assert "C-100" in node_ids
        assert "C-101" in node_ids
        assert "BR-001" in node_ids

        # Both code nodes should be at distance 0
        code_nodes = [n for n in data["nodes"] if n["id"] in ["C-100", "C-101"]]
        assert all(n["distance"] == 0 for n in code_nodes)

        # Upstream should be at distance 1 (from either code node)
        br_node = [n for n in data["nodes"] if n["id"] == "BR-001"][0]
        assert br_node["distance"] == 1

    def test_depth_zero(self, handler, sample_index_with_code, monkeypatch):
        """Test with depth 0 - should only return direct file nodes."""
        monkeypatch.chdir(sample_index_with_code)

        result = handler.handle(
            file_path="src/logging/api.py",
            depth=0,
            format="json"
        )

        data = json.loads(result)

        # Should only find C-120 (the direct node)
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["id"] == "C-120"
        assert data["nodes"][0]["distance"] == 0
