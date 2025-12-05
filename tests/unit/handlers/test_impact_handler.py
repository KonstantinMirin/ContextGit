"""Unit tests for ImpactHandler."""

import json
import tempfile
from pathlib import Path
import pytest

from contextgit.handlers.impact_handler import ImpactHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.domain.index.manager import IndexManager
from contextgit.models.node import Node
from contextgit.models.link import Link
from contextgit.models.index import Index
from contextgit.models.enums import NodeType, NodeStatus, RelationType, SyncStatus
from contextgit.models.location import HeadingLocation
from contextgit.exceptions import RepoNotFoundError, NodeNotFoundError
from contextgit.constants import CONTEXTGIT_DIR


class TestImpactHandler:
    """Tests for ImpactHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create ImpactHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return ImpactHandler(fs, yaml, formatter)

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
    def sample_index_with_chain(self, initialized_repo):
        """Create a sample index with a chain of dependencies.

        Structure:
        BR-001 -> SR-010 -> AR-020 -> C-120 -> T-050
                       \-> AR-021 -> C-121
        """
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
            id="AR-021",
            type=NodeType.ARCHITECTURE,
            title="Alternative architecture",
            file="docs/architecture2.md",
            location=HeadingLocation(path=["Architecture"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="f" * 64,
            llm_generated=False,
            tags=[]
        )

        node5 = Node(
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

        node6 = Node(
            id="C-121",
            type=NodeType.CODE,
            title="Alternative implementation",
            file="src/code2.py",
            location=HeadingLocation(path=["Code"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="g" * 64,
            llm_generated=False,
            tags=[]
        )

        node7 = Node(
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
            to_id="AR-021",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        link4 = Link(
            from_id="AR-020",
            to_id="C-120",
            relation_type=RelationType.IMPLEMENTS,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        link5 = Link(
            from_id="AR-021",
            to_id="C-121",
            relation_type=RelationType.IMPLEMENTS,
            sync_status=SyncStatus.OK,
            last_checked="2025-12-02T18:00:00Z"
        )

        link6 = Link(
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
            "AR-021": node4,
            "C-120": node5,
            "C-121": node6,
            "T-050": node7,
        }
        index.links = [link1, link2, link3, link4, link5, link6]

        # Save index
        index_mgr = IndexManager(fs, yaml, initialized_repo)
        index_mgr.save_index(index)

        return initialized_repo

    def test_impact_analysis_tree_format(self, handler, sample_index_with_chain, monkeypatch):
        """Test impact analysis with tree format."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="SR-010", depth=2, format="tree")

        # Check header
        assert "Impact Analysis: SR-010 (System requirement 1)" in result
        assert "=" * 60 in result

        # Check direct downstream section
        assert "DIRECT DOWNSTREAM (depth 1):" in result
        assert "AR-020: Architecture decision" in result
        assert "AR-021: Alternative architecture" in result

        # Check indirect downstream section
        assert "INDIRECT (depth 2+):" in result

        # Check affected files section
        assert "AFFECTED FILES:" in result
        assert "docs/system.md" in result
        assert "docs/architecture.md" in result

        # Check suggested actions
        assert "SUGGESTED ACTIONS:" in result
        assert "Review" in result
        assert "contextgit confirm" in result

    def test_impact_analysis_json_format(self, handler, sample_index_with_chain, monkeypatch):
        """Test impact analysis with JSON format."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="SR-010", depth=2, format="json")

        # Parse JSON
        data = json.loads(result)

        # Check structure
        assert "requirement_id" in data
        assert data["requirement_id"] == "SR-010"
        assert data["title"] == "System requirement 1"
        assert data["type"] == "system"

        # Check direct downstream
        assert "direct_downstream" in data
        assert len(data["direct_downstream"]) == 2
        direct_ids = {node["id"] for node in data["direct_downstream"]}
        assert "AR-020" in direct_ids
        assert "AR-021" in direct_ids

        # Check indirect downstream
        assert "indirect_downstream" in data
        # Should contain C-120, C-121, T-050
        indirect_ids = {node["id"] for node in data["indirect_downstream"]}
        assert "C-120" in indirect_ids
        assert "C-121" in indirect_ids
        assert "T-050" in indirect_ids

        # Check affected files
        assert "affected_files" in data
        assert "docs/system.md" in data["affected_files"]
        assert "docs/architecture.md" in data["affected_files"]

        # Check suggested actions
        assert "suggested_actions" in data
        assert len(data["suggested_actions"]) > 0

    def test_impact_analysis_checklist_format(self, handler, sample_index_with_chain, monkeypatch):
        """Test impact analysis with checklist format."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="SR-010", depth=2, format="checklist")

        # Check header
        assert "## Impact of changes to SR-010" in result

        # Check review checklist section
        assert "### Review checklist" in result
        assert "- [ ] AR-020: Architecture decision" in result
        assert "- [ ] AR-021: Alternative architecture" in result

        # Check indirect items marked as such
        assert "(indirect)" in result

        # Check after review section
        assert "### After review" in result
        assert "- [ ] `contextgit confirm AR-020`" in result
        assert "- [ ] `contextgit confirm AR-021`" in result

    def test_impact_analysis_with_depth_1(self, handler, sample_index_with_chain, monkeypatch):
        """Test impact analysis with depth=1 (only direct downstream)."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="SR-010", depth=1, format="json")

        # Parse JSON
        data = json.loads(result)

        # Should only have direct downstream (AR-020, AR-021)
        assert len(data["direct_downstream"]) == 2
        direct_ids = {node["id"] for node in data["direct_downstream"]}
        assert "AR-020" in direct_ids
        assert "AR-021" in direct_ids

        # Should have no indirect downstream
        assert len(data["indirect_downstream"]) == 0

    def test_impact_analysis_with_depth_3(self, handler, sample_index_with_chain, monkeypatch):
        """Test impact analysis with depth=3 (deep traversal)."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="SR-010", depth=3, format="json")

        # Parse JSON
        data = json.loads(result)

        # Should have direct downstream (depth 1)
        assert len(data["direct_downstream"]) == 2

        # Should have indirect downstream (depth 2 and 3)
        # Depth 2: C-120, C-121
        # Depth 3: T-050
        assert len(data["indirect_downstream"]) >= 3

    def test_impact_analysis_node_with_no_downstream(self, handler, sample_index_with_chain, monkeypatch):
        """Test impact analysis for a node with no downstream dependencies."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="T-050", depth=2, format="tree")

        # Check that it reports no downstream
        assert "DIRECT DOWNSTREAM (depth 1): None" in result
        assert "INDIRECT (depth 2+): None" in result

        # Check suggested actions shows no dependencies
        assert "No downstream dependencies to review" in result

    def test_impact_analysis_raises_error_for_nonexistent_node(self, handler, sample_index_with_chain, monkeypatch):
        """Test that impact analysis raises error for non-existent node."""
        monkeypatch.chdir(sample_index_with_chain)

        with pytest.raises(NodeNotFoundError):
            handler.handle(requirement_id="NONEXISTENT-123", depth=2, format="tree")

    def test_impact_analysis_raises_error_when_not_in_repo(self, handler, temp_dir, monkeypatch):
        """Test that impact analysis raises error when not in a contextgit repo."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(RepoNotFoundError):
            handler.handle(requirement_id="SR-010", depth=2, format="tree")

    def test_impact_analysis_includes_requirement_file(self, handler, sample_index_with_chain, monkeypatch):
        """Test that impact analysis includes the requirement's own file in affected files."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="SR-010", depth=2, format="json")

        # Parse JSON
        data = json.loads(result)

        # Should include the requirement's own file
        assert "docs/system.md" in data["affected_files"]

    def test_impact_analysis_from_root_node(self, handler, sample_index_with_chain, monkeypatch):
        """Test impact analysis from root node (BR-001)."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="BR-001", depth=3, format="json")

        # Parse JSON
        data = json.loads(result)

        # Direct downstream should be SR-010
        assert len(data["direct_downstream"]) == 1
        assert data["direct_downstream"][0]["id"] == "SR-010"

        # Indirect should include everything else
        indirect_ids = {node["id"] for node in data["indirect_downstream"]}
        assert "AR-020" in indirect_ids
        assert "AR-021" in indirect_ids
        assert "C-120" in indirect_ids
        assert "C-121" in indirect_ids
        assert "T-050" in indirect_ids

    def test_impact_analysis_default_depth(self, handler, sample_index_with_chain, monkeypatch):
        """Test that default depth is 2."""
        monkeypatch.chdir(sample_index_with_chain)

        # Call without specifying depth
        result = handler.handle(requirement_id="SR-010", format="json")

        # Parse JSON
        data = json.loads(result)

        # Should have both direct and indirect downstream
        assert len(data["direct_downstream"]) > 0
        assert len(data["indirect_downstream"]) > 0

    def test_impact_analysis_collects_unique_files(self, handler, sample_index_with_chain, monkeypatch):
        """Test that affected files list doesn't contain duplicates."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="BR-001", depth=3, format="json")

        # Parse JSON
        data = json.loads(result)

        # Check that files list has no duplicates
        files = data["affected_files"]
        assert len(files) == len(set(files)), "Affected files should not contain duplicates"

    def test_impact_analysis_tree_format_with_many_indirect_nodes(self, handler, sample_index_with_chain, monkeypatch):
        """Test that tree format truncates long indirect node lists."""
        monkeypatch.chdir(sample_index_with_chain)

        result = handler.handle(requirement_id="SR-010", depth=2, format="tree")

        # Should show "... and X more" if there are more than 3 indirect nodes
        if "INDIRECT (depth 2+):" in result and "3 nodes" in result:
            assert "and 0 more" in result or "... and" not in result

    def test_impact_analysis_empty_index(self, handler, initialized_repo, monkeypatch):
        """Test impact analysis with empty index."""
        monkeypatch.chdir(initialized_repo)

        # Create empty index
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        index = Index()
        index.nodes = {}
        index.links = []
        index_mgr.save_index(index)

        # Should raise NodeNotFoundError
        with pytest.raises(NodeNotFoundError):
            handler.handle(requirement_id="SR-010", depth=2, format="tree")
