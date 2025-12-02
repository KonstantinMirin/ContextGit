"""Unit tests for StatusHandler."""

import json
import tempfile
from pathlib import Path
import pytest

from contextgit.handlers.status_handler import StatusHandler
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
from contextgit.constants import CONTEXTGIT_DIR


class TestStatusHandler:
    """Tests for StatusHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create StatusHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return StatusHandler(fs, yaml, formatter)

    @pytest.fixture
    def initialized_repo(self, temp_dir):
        """Create an initialized contextgit repository."""
        # Create .contextgit directory
        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        contextgit_dir.mkdir(parents=True, exist_ok=True)

        # Create config
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
            title="Business requirement 1",
            file="docs/requirements.md",
            location=HeadingLocation(path=["Business Requirements"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )

        node2 = Node(
            id="SR-010",
            type=NodeType.SYSTEM,
            title="System requirement 1",
            file="docs/system.md",
            location=HeadingLocation(path=["System Design"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
            llm_generated=False,
            tags=[]
        )

        node3 = Node(
            id="AR-020",
            type=NodeType.ARCHITECTURE,
            title="Architecture decision",
            file="docs/architecture.md",
            location=HeadingLocation(path=["Architecture"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="c" * 64,
            llm_generated=False,
            tags=[]
        )

        node4 = Node(
            id="C-120",
            type=NodeType.CODE,
            title="Implementation",
            file="src/code.py",
            location=HeadingLocation(path=["Code"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="d" * 64,
            llm_generated=False,
            tags=[]
        )

        node5 = Node(
            id="T-050",
            type=NodeType.TEST,
            title="Test case",
            file="tests/test_code.py",
            location=HeadingLocation(path=["Tests"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="e" * 64,
            llm_generated=False,
            tags=[]
        )

        # Create links with various statuses
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
            sync_status=SyncStatus.UPSTREAM_CHANGED,
            last_checked="2025-12-02T18:00:00Z"
        )

        link3 = Link(
            from_id="AR-020",
            to_id="C-120",
            relation_type=RelationType.IMPLEMENTS,
            sync_status=SyncStatus.DOWNSTREAM_CHANGED,
            last_checked="2025-12-02T18:00:00Z"
        )

        link4 = Link(
            from_id="C-120",
            to_id="T-050",
            relation_type=RelationType.TESTS,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        # Create index
        index = Index()
        index.nodes = {
            "BR-001": node1,
            "SR-010": node2,
            "AR-020": node3,
            "C-120": node4,
            "T-050": node5,
        }
        index.links = [link1, link2, link3, link4]

        # Save index
        index_mgr = IndexManager(fs, yaml, initialized_repo)
        index_mgr.save_index(index)

        return initialized_repo

    def test_status_displays_basic_summary_text_format(self, handler, sample_index, monkeypatch):
        """Test that status displays basic summary in text format."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(format="text")

        # Check header
        assert "contextgit status:" in result

        # Check node counts
        assert "Nodes:" in result
        assert "business: 1" in result
        assert "system: 1" in result
        assert "architecture: 1" in result
        assert "code: 1" in result
        assert "test: 1" in result

        # Check link counts
        assert "Links: 4" in result

        # Check health section
        assert "Health:" in result
        assert "Stale links: 2" in result  # 2 non-OK links

    def test_status_displays_basic_summary_json_format(self, handler, sample_index, monkeypatch):
        """Test that status displays basic summary in JSON format."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(format="json")

        # Parse JSON
        data = json.loads(result)

        # Check structure
        assert "nodes" in data
        assert "links" in data

        # Check node counts
        assert data["nodes"]["business"] == 1
        assert data["nodes"]["system"] == 1
        assert data["nodes"]["architecture"] == 1
        assert data["nodes"]["code"] == 1
        assert data["nodes"]["test"] == 1

        # Check link counts
        assert data["links"]["total"] == 4
        assert data["links"]["stale"] == 2

    def test_status_with_stale_flag_text_format(self, handler, sample_index, monkeypatch):
        """Test status with --stale flag in text format."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(stale=True, format="text")

        # Check header
        assert "Stale links (need review):" in result

        # Check upstream changed section
        assert "Upstream changed:" in result
        assert "SR-010 → AR-020" in result
        assert "last checked: 2025-12-02T18:00:00Z" in result

        # Check downstream changed section
        assert "Downstream changed:" in result
        assert "AR-020 → C-120" in result

        # Check footer
        assert "Run 'contextgit confirm <ID>' to mark as synchronized." in result

    def test_status_with_stale_flag_json_format(self, handler, sample_index, monkeypatch):
        """Test status with --stale flag in JSON format."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(stale=True, format="json")

        # Parse JSON
        data = json.loads(result)

        # Check structure
        assert "stale_links" in data
        assert len(data["stale_links"]) == 2

        # Check link data
        stale_link_ids = [(link["from_id"], link["to_id"]) for link in data["stale_links"]]
        assert ("SR-010", "AR-020") in stale_link_ids
        assert ("AR-020", "C-120") in stale_link_ids

    def test_status_with_orphans_flag_text_format(self, handler, initialized_repo, monkeypatch):
        """Test status with --orphans flag in text format."""
        monkeypatch.chdir(initialized_repo)

        # Create index with orphan nodes
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        # Create nodes with orphans
        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Business req (no downstream)",
            file="docs/business.md",
            location=HeadingLocation(path=["Business"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )

        node2 = Node(
            id="C-100",
            type=NodeType.CODE,
            title="Code (no upstream)",
            file="src/code.py",
            location=HeadingLocation(path=["Code"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
            llm_generated=False,
            tags=[]
        )

        node3 = Node(
            id="SR-010",
            type=NodeType.SYSTEM,
            title="System (no downstream)",
            file="docs/system.md",
            location=HeadingLocation(path=["System"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="c" * 64,
            llm_generated=False,
            tags=[]
        )

        index = Index()
        index.nodes = {"BR-001": node1, "C-100": node2, "SR-010": node3}
        index.links = []  # No links - all are orphans
        index_mgr.save_index(index)

        result = handler.handle(orphans=True, format="text")

        # Check header
        assert "Orphan nodes:" in result

        # Check no upstream section (C-100 and SR-010 should be listed)
        assert "No upstream:" in result
        assert 'C-100: "Code (no upstream)" (code)' in result
        assert 'SR-010: "System (no downstream)" (system)' in result

        # Check no downstream section (BR-001 and SR-010 should be listed)
        # Note: Business nodes don't need upstream, code nodes don't need downstream
        assert "No downstream:" in result
        assert 'SR-010: "System (no downstream)" (system)' in result

    def test_status_with_orphans_flag_json_format(self, handler, initialized_repo, monkeypatch):
        """Test status with --orphans flag in JSON format."""
        monkeypatch.chdir(initialized_repo)

        # Create index with orphan nodes
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        node1 = Node(
            id="SR-010",
            type=NodeType.SYSTEM,
            title="Orphan system requirement",
            file="docs/system.md",
            location=HeadingLocation(path=["System"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )

        index = Index()
        index.nodes = {"SR-010": node1}
        index.links = []
        index_mgr.save_index(index)

        result = handler.handle(orphans=True, format="json")

        # Parse JSON
        data = json.loads(result)

        # Check structure
        assert "orphan_nodes" in data
        assert "no_upstream" in data["orphan_nodes"]
        assert "no_downstream" in data["orphan_nodes"]

        # SR-010 should be in both lists (system node needs both upstream and downstream)
        assert "SR-010" in data["orphan_nodes"]["no_upstream"]
        assert "SR-010" in data["orphan_nodes"]["no_downstream"]

    def test_status_with_no_stale_links(self, handler, initialized_repo, monkeypatch):
        """Test status --stale when there are no stale links."""
        monkeypatch.chdir(initialized_repo)

        # Create index with all OK links
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Business req",
            file="docs/business.md",
            location=HeadingLocation(path=["Business"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )

        node2 = Node(
            id="SR-010",
            type=NodeType.SYSTEM,
            title="System req",
            file="docs/system.md",
            location=HeadingLocation(path=["System"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
            llm_generated=False,
            tags=[]
        )

        link = Link(
            from_id="BR-001",
            to_id="SR-010",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        index = Index()
        index.nodes = {"BR-001": node1, "SR-010": node2}
        index.links = [link]
        index_mgr.save_index(index)

        result = handler.handle(stale=True, format="text")

        assert result == "No stale links"

    def test_status_with_no_orphan_nodes(self, handler, initialized_repo, monkeypatch):
        """Test status --orphans when there are no orphan nodes."""
        monkeypatch.chdir(initialized_repo)

        # Create index with properly linked nodes
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Business req",
            file="docs/business.md",
            location=HeadingLocation(path=["Business"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )

        node2 = Node(
            id="C-100",
            type=NodeType.CODE,
            title="Code",
            file="src/code.py",
            location=HeadingLocation(path=["Code"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
            llm_generated=False,
            tags=[]
        )

        link = Link(
            from_id="BR-001",
            to_id="C-100",
            relation_type=RelationType.IMPLEMENTS,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        index = Index()
        index.nodes = {"BR-001": node1, "C-100": node2}
        index.links = [link]
        index_mgr.save_index(index)

        result = handler.handle(orphans=True, format="text")

        assert result == "No orphan nodes"

    def test_status_raises_error_when_not_in_repo(self, handler, temp_dir, monkeypatch):
        """Test that status raises RepoNotFoundError when not in a contextgit repo."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(RepoNotFoundError) as exc_info:
            handler.handle(format="text")

        assert "Not in a contextgit repository" in str(exc_info.value)

    def test_status_with_broken_links(self, handler, initialized_repo, monkeypatch):
        """Test status with broken links."""
        monkeypatch.chdir(initialized_repo)

        # Create index with broken link
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Business req",
            file="docs/business.md",
            location=HeadingLocation(path=["Business"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )

        link = Link(
            from_id="BR-001",
            to_id="SR-999",  # Non-existent node
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.BROKEN,
            last_checked="2025-12-02T18:00:00Z"
        )

        index = Index()
        index.nodes = {"BR-001": node1}
        index.links = [link]
        index_mgr.save_index(index)

        result = handler.handle(stale=True, format="text")

        # Check broken section appears
        assert "Broken:" in result
        assert "BR-001 → SR-999" in result

    def test_status_empty_index(self, handler, initialized_repo, monkeypatch):
        """Test status with empty index."""
        monkeypatch.chdir(initialized_repo)

        # Create empty index
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        index = Index()
        index.nodes = {}
        index.links = []
        index_mgr.save_index(index)

        result = handler.handle(format="text")

        # Should display with zero counts
        assert "contextgit status:" in result
        assert "Links: 0" in result
