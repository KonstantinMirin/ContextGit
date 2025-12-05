"""Link model for contextgit.

contextgit:
  id: C-125
  type: code
  title: "Link Model - Traceability Relationship Definition"
  status: active
  upstream: [SR-012]
  tags: [models, dataclass, fr-4, traceability]

This module defines the Link class, representing a traceability relationship
between two nodes. Links track upstream/downstream relationships and their
synchronization status.
"""

from dataclasses import dataclass, field
from .enums import RelationType, SyncStatus


@dataclass
class Link:
    """Represents a traceability relationship between two nodes.

    Links are directed relationships from a source (upstream) node to a
    target (downstream) node. They track the relationship type and whether
    the link is still synchronized (i.e., whether either node has changed
    since the link was established).

    Attributes:
        from_id: Source node ID (upstream)
        to_id: Target node ID (downstream)
        relation_type: Type of relationship (refines, implements, tests, etc.)
        sync_status: Synchronization status (ok, upstream_changed, etc.)
        last_checked: ISO 8601 timestamp of last synchronization check
        skip_validation: If True, skip validation in __post_init__ (use when
                         validation has already been done by LinkingEngine)
    """

    from_id: str  # Source node ID (upstream)
    to_id: str    # Target node ID (downstream)
    relation_type: RelationType
    sync_status: SyncStatus
    last_checked: str  # ISO 8601 timestamp
    skip_validation: bool = field(default=False, repr=False, compare=False)

    def __post_init__(self):
        """Validate link data.

        Basic validation is always performed (non-empty IDs).
        Self-reference validation is skipped if skip_validation is True,
        which allows LinkingEngine to perform more sophisticated validation
        that considers file context (same-file parent-child links are allowed).
        """
        if not self.from_id or not self.to_id:
            raise ValueError("Link IDs cannot be empty")

        # Only perform basic self-reference check if validation not skipped
        # When skip_validation is True, LinkingEngine has already validated
        # with file context (allowing same-file parent-child relationships)
        if not self.skip_validation and self.from_id == self.to_id:
            raise ValueError(
                f"Self-referential link not allowed: {self.from_id} -> {self.to_id}\n"
                "Note: Use LinkingEngine.validate_link() for file-aware validation "
                "that allows same-file parent-child relationships."
            )

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization.

        Returns:
            Dictionary representation of the link.
        """
        return {
            'from': self.from_id,
            'to': self.to_id,
            'relation_type': self.relation_type.value,
            'sync_status': self.sync_status.value,
            'last_checked': self.last_checked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Link':
        """Create Link from dictionary (YAML deserialization).

        Args:
            data: Dictionary containing link data from YAML

        Returns:
            Link instance with data from dictionary.
        """
        return cls(
            from_id=data['from'],
            to_id=data['to'],
            relation_type=RelationType(data['relation_type']),
            sync_status=SyncStatus(data['sync_status']),
            last_checked=data['last_checked'],
        )
