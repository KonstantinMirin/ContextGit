"""Unit tests for LinkHandler."""

import json
import tempfile
from pathlib import Path
import pytest

from contextgit.handlers.link_handler import LinkHandler
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
from contextgit.constants import CONTEXTGIT_DIR


class TestLinkHandler:
    """Tests for LinkHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create LinkHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return LinkHandler(fs, yaml, formatter)

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
    def sample_index(self, initialized_repo):
        """Create a sample index with nodes."""
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
            location=HeadingLocation(path=["System Requirements"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="b" * 64,
            llm_generated=False,
            tags=[]
        )

        node3 = Node(
            id="AR-020",
            type=NodeType.ARCHITECTURE,
            title="Architecture design",
            file="docs/architecture.md",
            location=HeadingLocation(path=["Architecture"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="c" * 64,
            llm_generated=False,
            tags=[]
        )

        # Create index with nodes but no links
        index = Index()
        index.nodes = {
            "BR-001": node1,
            "SR-010": node2,
            "AR-020": node3,
        }
        index.links = []

        # Save index
        index_mgr = IndexManager(fs, yaml, initialized_repo)
        index_mgr.save_index(index)

        return initialized_repo

    def test_create_link_text_format(self, handler, sample_index, monkeypatch):
        """Test creating a new link with text output."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="text"
        )

        # Check output message
        assert "Created link: BR-001 -> SR-010 (refines)" in result

        # Verify link was saved to index
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, sample_index)
        index = index_mgr.load_index()

        assert len(index.links) == 1
        link = index.links[0]
        assert link.from_id == "BR-001"
        assert link.to_id == "SR-010"
        assert link.relation_type == RelationType.REFINES
        assert link.sync_status == SyncStatus.OK

    def test_create_link_json_format(self, handler, sample_index, monkeypatch):
        """Test creating a new link with JSON output."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="json"
        )

        # Parse JSON
        data = json.loads(result)

        # Check JSON structure
        assert data["status"] == "created"
        assert data["link"]["from"] == "BR-001"
        assert data["link"]["to"] == "SR-010"
        assert data["link"]["relation_type"] == "refines"
        assert data["link"]["sync_status"] == "ok"
        assert "last_checked" in data["link"]

    def test_create_link_all_relation_types(self, handler, sample_index, monkeypatch):
        """Test creating links with all relation types."""
        monkeypatch.chdir(sample_index)

        relation_types = ["refines", "implements", "tests", "derived_from", "depends_on"]

        for i, rel_type in enumerate(relation_types):
            # Use different node pairs to avoid duplicate link errors
            from_id = "BR-001"
            to_id = ["SR-010", "AR-020"][i % 2]

            if i > 1:
                # Add more nodes for testing
                from_id = ["SR-010", "AR-020"][i % 2]
                to_id = "BR-001"

            result = handler.handle(
                from_id=from_id,
                to_id=to_id,
                relation_type=rel_type,
                format="text"
            )

            assert f"({rel_type})" in result

    def test_update_existing_link(self, handler, sample_index, monkeypatch):
        """Test updating an existing link's relation type."""
        monkeypatch.chdir(sample_index)

        # Create initial link
        handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="text"
        )

        # Update the link
        result = handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="implements",
            format="text"
        )

        # Check output message
        assert "Updated link: BR-001 -> SR-010 (relation changed to: implements)" in result

        # Verify link was updated
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, sample_index)
        index = index_mgr.load_index()

        assert len(index.links) == 1  # Still only one link
        link = index.links[0]
        assert link.relation_type == RelationType.IMPLEMENTS  # Updated

    def test_update_existing_link_json_format(self, handler, sample_index, monkeypatch):
        """Test updating an existing link with JSON output."""
        monkeypatch.chdir(sample_index)

        # Create initial link
        handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="text"
        )

        # Update the link
        result = handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="implements",
            format="json"
        )

        # Parse JSON
        data = json.loads(result)

        # Check JSON structure
        assert data["status"] == "updated"
        assert data["link"]["from"] == "BR-001"
        assert data["link"]["to"] == "SR-010"
        assert data["link"]["relation_type"] == "implements"

    def test_link_raises_error_for_nonexistent_from_node(self, handler, sample_index, monkeypatch):
        """Test that link raises NodeNotFoundError for nonexistent source node."""
        monkeypatch.chdir(sample_index)

        with pytest.raises(NodeNotFoundError) as exc_info:
            handler.handle(
                from_id="BR-999",
                to_id="SR-010",
                relation_type="refines",
                format="text"
            )

        assert "BR-999" in str(exc_info.value)

    def test_link_raises_error_for_nonexistent_to_node(self, handler, sample_index, monkeypatch):
        """Test that link raises NodeNotFoundError for nonexistent target node."""
        monkeypatch.chdir(sample_index)

        with pytest.raises(NodeNotFoundError) as exc_info:
            handler.handle(
                from_id="BR-001",
                to_id="SR-999",
                relation_type="refines",
                format="text"
            )

        assert "SR-999" in str(exc_info.value)

    def test_link_raises_error_for_invalid_relation_type(self, handler, sample_index, monkeypatch):
        """Test that link raises ValueError for invalid relation type."""
        monkeypatch.chdir(sample_index)

        with pytest.raises(ValueError) as exc_info:
            handler.handle(
                from_id="BR-001",
                to_id="SR-010",
                relation_type="invalid_type",
                format="text"
            )

        assert "Invalid relation type: invalid_type" in str(exc_info.value)
        assert "refines" in str(exc_info.value)
        assert "implements" in str(exc_info.value)

    def test_link_raises_error_when_not_in_repo(self, handler, temp_dir, monkeypatch):
        """Test that link raises RepoNotFoundError when not in a contextgit repo."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(RepoNotFoundError):
            handler.handle(
                from_id="BR-001",
                to_id="SR-010",
                relation_type="refines",
                format="text"
            )

    def test_link_sets_sync_status_to_ok(self, handler, sample_index, monkeypatch):
        """Test that newly created links have sync_status set to ok."""
        monkeypatch.chdir(sample_index)

        handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="text"
        )

        # Verify sync status
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, sample_index)
        index = index_mgr.load_index()

        link = index.links[0]
        assert link.sync_status == SyncStatus.OK

    def test_link_updates_last_checked_timestamp(self, handler, sample_index, monkeypatch):
        """Test that link creates/updates last_checked timestamp."""
        monkeypatch.chdir(sample_index)

        result = handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="json"
        )

        data = json.loads(result)
        assert "last_checked" in data["link"]
        # Should be ISO 8601 format
        assert "T" in data["link"]["last_checked"]
        assert "Z" in data["link"]["last_checked"]

    def test_link_multiple_links_from_same_node(self, handler, sample_index, monkeypatch):
        """Test creating multiple links from the same source node."""
        monkeypatch.chdir(sample_index)

        # Create two links from BR-001
        handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="text"
        )

        handler.handle(
            from_id="BR-001",
            to_id="AR-020",
            relation_type="refines",
            format="text"
        )

        # Verify both links exist
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, sample_index)
        index = index_mgr.load_index()

        assert len(index.links) == 2
        from_ids = [link.from_id for link in index.links]
        assert from_ids.count("BR-001") == 2

    def test_link_multiple_links_to_same_node(self, handler, sample_index, monkeypatch):
        """Test creating multiple links to the same target node."""
        monkeypatch.chdir(sample_index)

        # Create two links to SR-010
        handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="text"
        )

        handler.handle(
            from_id="AR-020",
            to_id="SR-010",
            relation_type="implements",
            format="text"
        )

        # Verify both links exist
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, sample_index)
        index = index_mgr.load_index()

        assert len(index.links) == 2
        to_ids = [link.to_id for link in index.links]
        assert to_ids.count("SR-010") == 2

    def test_link_preserves_other_links(self, handler, sample_index, monkeypatch):
        """Test that creating a new link preserves existing links."""
        monkeypatch.chdir(sample_index)

        # Create first link
        handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="refines",
            format="text"
        )

        # Create second link
        handler.handle(
            from_id="SR-010",
            to_id="AR-020",
            relation_type="implements",
            format="text"
        )

        # Verify both links exist
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, sample_index)
        index = index_mgr.load_index()

        assert len(index.links) == 2

    def test_update_link_resets_sync_status_to_ok(self, handler, initialized_repo, monkeypatch):
        """Test that updating a link resets sync_status to ok."""
        monkeypatch.chdir(initialized_repo)

        # Create index with a stale link
        fs = FileSystem()
        yaml = YAMLSerializer()
        index_mgr = IndexManager(fs, yaml, initialized_repo)

        node1 = Node(
            id="BR-001",
            type=NodeType.BUSINESS,
            title="Business requirement",
            file="docs/requirements.md",
            location=HeadingLocation(path=["Requirements"]),
            status=NodeStatus.ACTIVE,
            last_updated="2025-12-02T18:00:00Z",
            checksum="a" * 64,
            llm_generated=False,
            tags=[]
        )

        node2 = Node(
            id="SR-010",
            type=NodeType.SYSTEM,
            title="System requirement",
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
            sync_status=SyncStatus.UPSTREAM_CHANGED,  # Stale
            last_checked="2025-12-01T18:00:00Z"
        )

        index = Index()
        index.nodes = {"BR-001": node1, "SR-010": node2}
        index.links = [link]
        index_mgr.save_index(index)

        # Update the link
        handler.handle(
            from_id="BR-001",
            to_id="SR-010",
            relation_type="implements",
            format="text"
        )

        # Verify sync_status was reset to ok
        index = index_mgr.load_index()
        updated_link = index.links[0]
        assert updated_link.sync_status == SyncStatus.OK
