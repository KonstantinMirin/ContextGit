"""Unit tests for LinkingEngine validation and circular dependency detection."""

import pytest
from datetime import datetime, timezone

from contextgit.domain.linking.engine import LinkingEngine
from contextgit.models.node import Node
from contextgit.models.link import Link
from contextgit.models.index import Index
from contextgit.models.enums import NodeType, NodeStatus, RelationType, SyncStatus
from contextgit.models.location import HeadingLocation
from contextgit.exceptions import SelfReferentialError, CircularDependencyError


class TestLinkValidation:
    """Tests for link validation logic."""

    @pytest.fixture
    def engine(self):
        """Create LinkingEngine instance."""
        return LinkingEngine()

    @pytest.fixture
    def sample_nodes(self):
        """Create sample nodes for testing."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "SR-001": Node(
                id="SR-001",
                type=NodeType.SYSTEM,
                title="Parent requirement",
                file="docs/requirements.md",
                location=HeadingLocation(path=["Requirements", "Parent"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="a" * 64,
                llm_generated=False,
                tags=[]
            ),
            "SR-002": Node(
                id="SR-002",
                type=NodeType.SYSTEM,
                title="Child requirement",
                file="docs/requirements.md",  # Same file as SR-001
                location=HeadingLocation(path=["Requirements", "Child"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="b" * 64,
                llm_generated=False,
                tags=[]
            ),
            "SR-003": Node(
                id="SR-003",
                type=NodeType.SYSTEM,
                title="Other requirement",
                file="docs/other.md",  # Different file
                location=HeadingLocation(path=["Other"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="c" * 64,
                llm_generated=False,
                tags=[]
            ),
            "AR-001": Node(
                id="AR-001",
                type=NodeType.ARCHITECTURE,
                title="Architecture decision",
                file="docs/architecture.md",  # Different file
                location=HeadingLocation(path=["Architecture"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="d" * 64,
                llm_generated=False,
                tags=[]
            ),
        }

    def test_same_file_parent_child_allowed(self, engine, sample_nodes):
        """Parent-child links within same file should be allowed."""
        # SR-001 and SR-002 are in the same file
        # This should NOT raise an error
        result = engine.validate_link(
            from_id="SR-001",
            to_id="SR-002",
            nodes=sample_nodes,
            existing_links=[]
        )
        assert result is True

    def test_same_file_reverse_link_allowed(self, engine, sample_nodes):
        """Reverse links within same file should be allowed."""
        # SR-002 referencing SR-001 (child to parent) should also work
        result = engine.validate_link(
            from_id="SR-002",
            to_id="SR-001",
            nodes=sample_nodes,
            existing_links=[]
        )
        assert result is True

    def test_true_self_reference_blocked(self, engine, sample_nodes):
        """A node referencing itself should be blocked."""
        with pytest.raises(SelfReferentialError) as exc_info:
            engine.validate_link(
                from_id="SR-001",
                to_id="SR-001",  # Same as from_id
                nodes=sample_nodes,
                existing_links=[]
            )

        assert "SR-001" in str(exc_info.value)
        assert "references itself" in str(exc_info.value)
        assert exc_info.value.node_id == "SR-001"

    def test_cross_file_link_allowed(self, engine, sample_nodes):
        """Links between nodes in different files should be allowed (no cycle)."""
        result = engine.validate_link(
            from_id="SR-001",
            to_id="SR-003",
            nodes=sample_nodes,
            existing_links=[]
        )
        assert result is True

    def test_cross_file_circular_blocked(self, engine, sample_nodes):
        """Circular dependencies across files should be blocked."""
        now = datetime.now(timezone.utc).isoformat()

        # Create existing link: SR-003 -> AR-001
        existing_links = [
            Link(
                from_id="SR-003",
                to_id="AR-001",
                relation_type=RelationType.REFINES,
                sync_status=SyncStatus.OK,
                last_checked=now,
                skip_validation=True,
            ),
            # AR-001 -> SR-001
            Link(
                from_id="AR-001",
                to_id="SR-001",
                relation_type=RelationType.IMPLEMENTS,
                sync_status=SyncStatus.OK,
                last_checked=now,
                skip_validation=True,
            ),
        ]

        # Now trying to add SR-001 -> SR-003 would create a cycle
        # SR-001 -> SR-003 -> AR-001 -> SR-001
        with pytest.raises(CircularDependencyError):
            engine.validate_link(
                from_id="SR-001",
                to_id="SR-003",
                nodes=sample_nodes,
                existing_links=existing_links
            )

    def test_nonexistent_node_passes(self, engine, sample_nodes):
        """Links to/from nonexistent nodes pass validation (handled elsewhere)."""
        result = engine.validate_link(
            from_id="SR-001",
            to_id="SR-999",  # Doesn't exist
            nodes=sample_nodes,
            existing_links=[]
        )
        assert result is True

    def test_self_referential_error_has_file_info(self, engine, sample_nodes):
        """SelfReferentialError should include file information."""
        with pytest.raises(SelfReferentialError) as exc_info:
            engine.validate_link(
                from_id="SR-001",
                to_id="SR-001",
                nodes=sample_nodes,
                existing_links=[]
            )

        assert exc_info.value.file == "docs/requirements.md"


class TestCircularDependencyDetection:
    """Tests for circular dependency detection."""

    @pytest.fixture
    def engine(self):
        """Create LinkingEngine instance."""
        return LinkingEngine()

    def test_detect_cross_file_cycle(self, engine):
        """Should detect cycles that cross file boundaries."""
        now = datetime.now(timezone.utc).isoformat()

        index = Index()
        index.nodes = {
            "SR-001": Node(
                id="SR-001",
                type=NodeType.SYSTEM,
                title="Req 1",
                file="file_a.md",
                location=HeadingLocation(path=["A"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="a" * 64,
                llm_generated=False,
                tags=[]
            ),
            "SR-002": Node(
                id="SR-002",
                type=NodeType.SYSTEM,
                title="Req 2",
                file="file_b.md",  # Different file
                location=HeadingLocation(path=["B"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="b" * 64,
                llm_generated=False,
                tags=[]
            ),
        }
        index.links = [
            Link(
                from_id="SR-001",
                to_id="SR-002",
                relation_type=RelationType.REFINES,
                sync_status=SyncStatus.OK,
                last_checked=now,
                skip_validation=True,
            ),
            Link(
                from_id="SR-002",
                to_id="SR-001",
                relation_type=RelationType.REFINES,
                sync_status=SyncStatus.OK,
                last_checked=now,
                skip_validation=True,
            ),
        ]

        cycles = engine.detect_circular_dependencies(index)
        assert len(cycles) > 0

    def test_same_file_cycle_not_detected(self, engine):
        """Cycles within same file should not be reported."""
        now = datetime.now(timezone.utc).isoformat()

        index = Index()
        index.nodes = {
            "SR-001": Node(
                id="SR-001",
                type=NodeType.SYSTEM,
                title="Req 1",
                file="same_file.md",
                location=HeadingLocation(path=["A"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="a" * 64,
                llm_generated=False,
                tags=[]
            ),
            "SR-002": Node(
                id="SR-002",
                type=NodeType.SYSTEM,
                title="Req 2",
                file="same_file.md",  # Same file
                location=HeadingLocation(path=["B"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="b" * 64,
                llm_generated=False,
                tags=[]
            ),
        }
        index.links = [
            Link(
                from_id="SR-001",
                to_id="SR-002",
                relation_type=RelationType.REFINES,
                sync_status=SyncStatus.OK,
                last_checked=now,
                skip_validation=True,
            ),
            Link(
                from_id="SR-002",
                to_id="SR-001",
                relation_type=RelationType.REFINES,
                sync_status=SyncStatus.OK,
                last_checked=now,
                skip_validation=True,
            ),
        ]

        cycles = engine.detect_circular_dependencies(index)
        # Cycles within same file should not be detected as problematic
        assert len(cycles) == 0

    def test_no_cycles_returns_empty(self, engine):
        """When there are no cycles, return empty list."""
        now = datetime.now(timezone.utc).isoformat()

        index = Index()
        index.nodes = {
            "SR-001": Node(
                id="SR-001",
                type=NodeType.SYSTEM,
                title="Req 1",
                file="file_a.md",
                location=HeadingLocation(path=["A"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="a" * 64,
                llm_generated=False,
                tags=[]
            ),
            "SR-002": Node(
                id="SR-002",
                type=NodeType.SYSTEM,
                title="Req 2",
                file="file_b.md",
                location=HeadingLocation(path=["B"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="b" * 64,
                llm_generated=False,
                tags=[]
            ),
        }
        index.links = [
            Link(
                from_id="SR-001",
                to_id="SR-002",
                relation_type=RelationType.REFINES,
                sync_status=SyncStatus.OK,
                last_checked=now,
                skip_validation=True,
            ),
        ]

        cycles = engine.detect_circular_dependencies(index)
        assert len(cycles) == 0


class TestBuildLinksFromMetadata:
    """Tests for building links from metadata with validation."""

    @pytest.fixture
    def engine(self):
        """Create LinkingEngine instance."""
        return LinkingEngine()

    @pytest.fixture
    def sample_nodes(self):
        """Create sample nodes for testing."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "SR-001": Node(
                id="SR-001",
                type=NodeType.SYSTEM,
                title="Parent",
                file="docs/requirements.md",
                location=HeadingLocation(path=["Parent"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="a" * 64,
                llm_generated=False,
                tags=[]
            ),
            "SR-002": Node(
                id="SR-002",
                type=NodeType.SYSTEM,
                title="Child",
                file="docs/requirements.md",  # Same file
                location=HeadingLocation(path=["Child"]),
                status=NodeStatus.ACTIVE,
                last_updated=now,
                checksum="b" * 64,
                llm_generated=False,
                tags=[]
            ),
        }

    def test_builds_same_file_links(self, engine, sample_nodes):
        """Should successfully build links between nodes in same file."""
        from dataclasses import dataclass, field

        @dataclass
        class MockMetadata:
            upstream: list = field(default_factory=list)
            downstream: list = field(default_factory=list)

        metadata_map = {
            "SR-001": MockMetadata(upstream=[], downstream=["SR-002"]),
            "SR-002": MockMetadata(upstream=["SR-001"], downstream=[]),
        }

        links = engine.build_links_from_metadata(sample_nodes, metadata_map)

        # Should create 2 links (one from upstream, one from downstream)
        # But they're the same link, so we might get duplicates
        assert len(links) >= 1

        # Verify the link was created correctly
        link_pairs = [(l.from_id, l.to_id) for l in links]
        assert ("SR-001", "SR-002") in link_pairs

    def test_blocks_self_reference_in_metadata(self, engine, sample_nodes):
        """Should raise error if metadata contains self-reference."""
        from dataclasses import dataclass, field

        @dataclass
        class MockMetadata:
            upstream: list = field(default_factory=list)
            downstream: list = field(default_factory=list)

        metadata_map = {
            "SR-001": MockMetadata(upstream=["SR-001"], downstream=[]),  # Self-ref!
        }

        with pytest.raises(SelfReferentialError):
            engine.build_links_from_metadata(sample_nodes, metadata_map)


class TestLinkModel:
    """Tests for Link model validation."""

    def test_link_skip_validation_allows_same_id(self):
        """Link with skip_validation=True should skip self-reference check."""
        now = datetime.now(timezone.utc).isoformat()

        # This would normally raise, but skip_validation allows it
        # (for testing purposes - normally you wouldn't do this)
        link = Link(
            from_id="SR-001",
            to_id="SR-001",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked=now,
            skip_validation=True,
        )
        assert link.from_id == "SR-001"
        assert link.to_id == "SR-001"

    def test_link_without_skip_validation_blocks_same_id(self):
        """Link without skip_validation should block self-reference."""
        now = datetime.now(timezone.utc).isoformat()

        with pytest.raises(ValueError) as exc_info:
            Link(
                from_id="SR-001",
                to_id="SR-001",
                relation_type=RelationType.REFINES,
                sync_status=SyncStatus.OK,
                last_checked=now,
            )

        assert "Self-referential link not allowed" in str(exc_info.value)

    def test_link_to_dict_excludes_skip_validation(self):
        """to_dict should not include skip_validation."""
        now = datetime.now(timezone.utc).isoformat()

        link = Link(
            from_id="SR-001",
            to_id="SR-002",
            relation_type=RelationType.REFINES,
            sync_status=SyncStatus.OK,
            last_checked=now,
            skip_validation=True,
        )

        data = link.to_dict()
        assert "skip_validation" not in data
        assert data["from"] == "SR-001"
        assert data["to"] == "SR-002"

    def test_link_from_dict_default_validation(self):
        """from_dict should create link with default skip_validation=False."""
        now = datetime.now(timezone.utc).isoformat()

        data = {
            "from": "SR-001",
            "to": "SR-002",
            "relation_type": "refines",
            "sync_status": "ok",
            "last_checked": now,
        }

        link = Link.from_dict(data)
        assert link.skip_validation is False
