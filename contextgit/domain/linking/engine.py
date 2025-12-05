"""Traceability linking and graph operations.

contextgit:
  id: C-103
  type: code
  title: "Linking Engine - Graph Operations and Sync Status"
  status: active
  upstream: [SR-012]
  tags: [domain, linking, fr-8, fr-9, graph-traversal]

This module implements the LinkingEngine class, which manages the creation
and maintenance of traceability links between nodes. It provides functionality
for building links from metadata, updating sync status, traversing the
traceability graph, and detecting orphan nodes.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from contextgit.models.index import Index
from contextgit.models.link import Link
from contextgit.models.node import Node
from contextgit.models.enums import NodeType, RelationType, SyncStatus
from contextgit.exceptions import SelfReferentialError, CircularDependencyError

if TYPE_CHECKING:
    # Forward reference to avoid circular import with metadata parser
    from typing import Any
    RawMetadata = Any


class LinkingEngine:
    """Manages traceability links and graph operations.

    The LinkingEngine is responsible for:
    - Building links from upstream/downstream metadata fields
    - Inferring relation types based on node types
    - Updating sync status when nodes change
    - Traversing the traceability graph (upstream/downstream)
    - Detecting orphan nodes without proper linkage
    """

    def build_links_from_metadata(
        self,
        nodes: dict[str, Node],
        metadata_map: dict[str, 'RawMetadata']
    ) -> list[Link]:
        """
        Build links based on upstream/downstream in metadata.

        Infers relation types based on node types.
        Validates links before creating them - allows same-file parent-child
        relationships but blocks true self-references.

        Args:
            nodes: All nodes in index
            metadata_map: Metadata for each node (with upstream/downstream fields)

        Returns:
            List of links to add to index

        Raises:
            SelfReferentialError: If a node references itself
        """
        links = []
        now = datetime.now(timezone.utc).isoformat()

        for node_id, metadata in metadata_map.items():
            # Create links from upstream
            for upstream_id in metadata.upstream:
                if upstream_id in nodes:
                    # Validate the link before creating it
                    self.validate_link(
                        from_id=upstream_id,
                        to_id=node_id,
                        nodes=nodes,
                        existing_links=links
                    )

                    relation = self._infer_relation_type(
                        nodes[upstream_id].type,
                        nodes[node_id].type
                    )
                    links.append(Link(
                        from_id=upstream_id,
                        to_id=node_id,
                        relation_type=relation,
                        sync_status=SyncStatus.OK,
                        last_checked=now,
                        skip_validation=True,  # Already validated
                    ))

            # Create links from downstream
            for downstream_id in metadata.downstream:
                if downstream_id in nodes:
                    # Validate the link before creating it
                    self.validate_link(
                        from_id=node_id,
                        to_id=downstream_id,
                        nodes=nodes,
                        existing_links=links
                    )

                    relation = self._infer_relation_type(
                        nodes[node_id].type,
                        nodes[downstream_id].type
                    )
                    links.append(Link(
                        from_id=node_id,
                        to_id=downstream_id,
                        relation_type=relation,
                        sync_status=SyncStatus.OK,
                        last_checked=now,
                        skip_validation=True,  # Already validated
                    ))

        return links

    def _infer_relation_type(
        self, from_type: NodeType, to_type: NodeType
    ) -> RelationType:
        """Infer relation type based on node types."""
        # code -> test: tests
        if to_type == NodeType.TEST:
            return RelationType.TESTS

        # business -> *: refines
        if from_type == NodeType.BUSINESS:
            return RelationType.REFINES

        # system -> code: implements
        # system -> architecture: refines
        if from_type == NodeType.SYSTEM:
            if to_type == NodeType.CODE:
                return RelationType.IMPLEMENTS
            return RelationType.REFINES

        # architecture -> code: implements
        if from_type == NodeType.ARCHITECTURE:
            return RelationType.IMPLEMENTS

        # Default
        return RelationType.REFINES

    def update_sync_status(
        self, index: Index, changed_node_ids: set[str]
    ) -> None:
        """
        Update sync status for links affected by changed nodes.

        Sets UPSTREAM_CHANGED or DOWNSTREAM_CHANGED as appropriate.

        Args:
            index: Index to update (modified in place)
            changed_node_ids: Set of node IDs that changed
        """
        now = datetime.now(timezone.utc).isoformat()

        for link in index.links:
            # If upstream node changed
            if link.from_id in changed_node_ids:
                link.sync_status = SyncStatus.UPSTREAM_CHANGED
                link.last_checked = now

            # If downstream node changed
            if link.to_id in changed_node_ids:
                link.sync_status = SyncStatus.DOWNSTREAM_CHANGED
                link.last_checked = now

    def get_upstream_nodes(
        self, index: Index, node_id: str, depth: int = 1
    ) -> list[Node]:
        """
        Get all upstream nodes up to specified depth.

        Uses breadth-first traversal.

        Args:
            index: Index to search
            node_id: Starting node
            depth: How many levels to traverse (default: 1)

        Returns:
            List of upstream nodes
        """
        visited = set()
        result = []

        def traverse(current_id: str, current_depth: int):
            if current_depth > depth or current_id in visited:
                return

            visited.add(current_id)

            # Find incoming links
            for link in index.links:
                if link.to_id == current_id and link.from_id not in visited:
                    upstream_node = index.nodes.get(link.from_id)
                    if upstream_node:
                        result.append(upstream_node)
                        traverse(link.from_id, current_depth + 1)

        traverse(node_id, 0)
        return result

    def get_downstream_nodes(
        self, index: Index, node_id: str, depth: int = 1
    ) -> list[Node]:
        """
        Get all downstream nodes up to specified depth.

        Uses breadth-first traversal.

        Args:
            index: Index to search
            node_id: Starting node
            depth: How many levels to traverse (default: 1)

        Returns:
            List of downstream nodes
        """
        visited = set()
        result = []

        def traverse(current_id: str, current_depth: int):
            if current_depth > depth or current_id in visited:
                return

            visited.add(current_id)

            # Find outgoing links
            for link in index.links:
                if link.from_id == current_id and link.to_id not in visited:
                    downstream_node = index.nodes.get(link.to_id)
                    if downstream_node:
                        result.append(downstream_node)
                        traverse(link.to_id, current_depth + 1)

        traverse(node_id, 0)
        return result

    def detect_orphans(
        self, index: Index
    ) -> tuple[list[str], list[str]]:
        """
        Detect orphan nodes (no upstream or no downstream).

        Business nodes don't need upstream.
        Code/test nodes don't need downstream.

        Args:
            index: Index to analyze

        Returns:
            Tuple of (nodes_without_upstream, nodes_without_downstream)
        """
        no_upstream = []
        no_downstream = []

        # Build sets of nodes with links
        has_upstream = set()
        has_downstream = set()

        for link in index.links:
            has_downstream.add(link.from_id)
            has_upstream.add(link.to_id)

        # Check each node
        for node_id, node in index.nodes.items():
            # Business requirements don't need upstream
            if node.type != NodeType.BUSINESS and node_id not in has_upstream:
                no_upstream.append(node_id)

            # Code and test don't need downstream
            if node.type not in (NodeType.CODE, NodeType.TEST) and node_id not in has_downstream:
                no_downstream.append(node_id)

        return no_upstream, no_downstream

    def validate_link(
        self,
        from_id: str,
        to_id: str,
        nodes: dict[str, Node],
        existing_links: list[Link] = None
    ) -> bool:
        """
        Validate a link between two nodes.

        Returns True if link is valid. Same-file links are allowed (hierarchical).
        Only block true self-references and circular dependencies across files.

        Args:
            from_id: Source node ID (upstream)
            to_id: Target node ID (downstream)
            nodes: All nodes in index
            existing_links: Existing links for cycle detection

        Returns:
            True if the link is valid

        Raises:
            SelfReferentialError: If from_id equals to_id (true self-reference)
            CircularDependencyError: If the link creates a cycle across files
        """
        # Block true self-references (node referencing itself)
        if from_id == to_id:
            from_node = nodes.get(from_id)
            raise SelfReferentialError(
                node_id=from_id,
                file=from_node.file if from_node else None,
                line=None
            )

        # Get file paths for both nodes
        from_node = nodes.get(from_id)
        to_node = nodes.get(to_id)

        if not from_node or not to_node:
            # Can't validate if nodes don't exist
            return True

        # Same-file links are always allowed (parent-child hierarchy)
        if from_node.file == to_node.file:
            return True

        # Check for circular dependencies across files
        if existing_links:
            if self._creates_cycle(from_id, to_id, nodes, existing_links):
                raise CircularDependencyError(
                    cycle=[from_id, to_id],
                    message=f"Circular dependency detected: {from_id} -> {to_id}"
                )

        return True

    def _creates_cycle(
        self,
        from_id: str,
        to_id: str,
        nodes: dict[str, Node],
        existing_links: list[Link]
    ) -> bool:
        """
        Check if adding a link would create a circular dependency across files.

        Uses DFS to check if there's already a path from to_id back to from_id
        that crosses file boundaries.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            nodes: All nodes in index
            existing_links: Existing links to check

        Returns:
            True if adding the link would create a cycle across files
        """
        from_node = nodes.get(from_id)
        if not from_node:
            return False

        # Build adjacency list for faster traversal
        adjacency = {}
        for link in existing_links:
            if link.from_id not in adjacency:
                adjacency[link.from_id] = []
            adjacency[link.from_id].append(link.to_id)

        # DFS to find if there's a path from to_id back to from_id
        # that involves different files
        visited = set()

        def dfs(current_id: str, path: list[str]) -> bool:
            if current_id in visited:
                return False

            visited.add(current_id)
            path.append(current_id)

            if current_id == from_id and len(path) > 1:
                # Check if this cycle crosses file boundaries
                files_in_cycle = set()
                for node_id in path:
                    node = nodes.get(node_id)
                    if node:
                        files_in_cycle.add(node.file)

                # If multiple files involved, it's a cross-file cycle
                if len(files_in_cycle) > 1:
                    return True

            # Continue DFS
            for neighbor in adjacency.get(current_id, []):
                if dfs(neighbor, path.copy()):
                    return True

            return False

        return dfs(to_id, [])

    def detect_circular_dependencies(
        self, index: Index
    ) -> list[list[str]]:
        """
        Detect all circular dependencies in the index.

        Uses Tarjan's algorithm to find strongly connected components,
        then filters to only report cycles that cross file boundaries.

        Args:
            index: Index to analyze

        Returns:
            List of cycles, where each cycle is a list of node IDs
        """
        cycles = []

        # Build adjacency list
        adjacency = {}
        for link in index.links:
            if link.from_id not in adjacency:
                adjacency[link.from_id] = []
            adjacency[link.from_id].append(link.to_id)

        # Find all cycles using DFS
        visited = set()
        rec_stack = set()

        def find_cycles(node_id: str, path: list[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                if neighbor not in visited:
                    find_cycles(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle - extract it
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]

                    # Check if cycle crosses file boundaries
                    files_in_cycle = set()
                    for nid in cycle:
                        node = index.nodes.get(nid)
                        if node:
                            files_in_cycle.add(node.file)

                    if len(files_in_cycle) > 1:
                        cycles.append(cycle)

            rec_stack.discard(node_id)

        for node_id in index.nodes:
            if node_id not in visited:
                find_cycles(node_id, [])

        return cycles
