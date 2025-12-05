"""Handler for contextgit impact command.

contextgit:
  id: C-112
  type: code
  title: "Impact Handler - Downstream Impact Analysis"
  status: active
  upstream: [SR-012]
  tags: [cli, impact-analysis, graph-traversal]
"""

import json
from pathlib import Path
from contextgit.domain.index.manager import IndexManager
from contextgit.domain.linking.engine import LinkingEngine
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.exceptions import NodeNotFoundError, RepoNotFoundError


class ImpactHandler:
    """Handler for contextgit impact command.

    Analyzes the downstream impact of changing a requirement,
    showing all affected nodes and files.
    """

    def __init__(self, filesystem: FileSystem, yaml_io: YAMLSerializer, formatter: OutputFormatter):
        """Initialize ImpactHandler.

        Args:
            filesystem: File system abstraction
            yaml_io: YAML serialization handler
            formatter: Output formatter
        """
        self.fs = filesystem
        self.yaml = yaml_io
        self.formatter = formatter

    def find_repo_root(self) -> str:
        """Find repository root starting from current directory.

        Returns:
            Absolute path to repository root

        Raises:
            RepoNotFoundError: If not in a contextgit repository
        """
        try:
            return self.fs.find_repo_root(str(Path.cwd()))
        except FileNotFoundError:
            raise RepoNotFoundError("Not in a contextgit repository. Run 'contextgit init' first.")

    def handle(
        self,
        requirement_id: str,
        depth: int = 2,
        format: str = "tree"
    ) -> str:
        """
        Analyze impact of changing a requirement.

        Args:
            requirement_id: ID to analyze (e.g., SR-006)
            depth: Traversal depth (default 2)
            format: Output format (tree, json, checklist)

        Returns:
            Impact analysis in requested format

        Raises:
            NodeNotFoundError: If requirement doesn't exist
            RepoNotFoundError: If not in a contextgit repository
        """
        # Find repo root
        repo_root = self.find_repo_root()

        # Load index
        index_mgr = IndexManager(self.fs, self.yaml, repo_root)
        index = index_mgr.load_index()

        # Get the target node
        node = index_mgr.get_node(requirement_id)

        # Use LinkingEngine to get downstream nodes
        linking_engine = LinkingEngine()

        # Manually identify direct downstream (depth 1) by checking direct links
        direct_ids = set()
        for link in index.links:
            if link.from_id == requirement_id:
                direct_ids.add(link.to_id)

        # Get direct downstream nodes
        direct_downstream = [index.nodes[node_id] for node_id in direct_ids if node_id in index.nodes]

        # Get all downstream up to specified depth for indirect
        # If depth is 1, we only want direct downstream, so indirect should be empty
        if depth == 1:
            indirect_downstream = []
        else:
            all_downstream = linking_engine.get_downstream_nodes(index, requirement_id, depth)
            # Indirect downstream = all downstream - direct downstream
            indirect_downstream = [n for n in all_downstream if n.id not in direct_ids]

        # Collect affected files
        affected_files = set()
        affected_files.add(node.file)  # Include the requirement's own file
        for downstream_node in direct_downstream:
            affected_files.add(downstream_node.file)
        for downstream_node in indirect_downstream:
            affected_files.add(downstream_node.file)

        # Format output based on requested format
        if format == "json":
            return self._format_json(
                node,
                direct_downstream,
                indirect_downstream,
                affected_files
            )
        elif format == "checklist":
            return self._format_checklist(
                node,
                direct_downstream,
                indirect_downstream
            )
        else:  # tree format (default)
            return self._format_tree(
                node,
                direct_downstream,
                indirect_downstream,
                affected_files
            )

    def _format_tree(
        self,
        node,
        direct_downstream,
        indirect_downstream,
        affected_files
    ) -> str:
        """Format output as a tree view.

        Args:
            node: The target node being analyzed
            direct_downstream: List of direct downstream nodes
            indirect_downstream: List of indirect downstream nodes
            affected_files: Set of affected file paths

        Returns:
            Tree-formatted string
        """
        lines = []
        lines.append(f"Impact Analysis: {node.id} ({node.title})")
        lines.append("=" * 60)
        lines.append("")

        # Direct downstream
        if direct_downstream:
            lines.append("DIRECT DOWNSTREAM (depth 1):")
            for downstream_node in direct_downstream:
                lines.append(f"├── {downstream_node.id}: {downstream_node.title}")
                lines.append(f"│   └── Type: {downstream_node.type.value}, File: {downstream_node.file}")
            lines.append("")
        else:
            lines.append("DIRECT DOWNSTREAM (depth 1): None")
            lines.append("")

        # Indirect downstream
        if indirect_downstream:
            lines.append(f"INDIRECT (depth 2+): {len(indirect_downstream)} nodes")
            # Show first few indirect nodes
            shown_count = min(3, len(indirect_downstream))
            for i, downstream_node in enumerate(indirect_downstream[:shown_count]):
                if i == 0:
                    lines.append(f"└── {downstream_node.id}: {downstream_node.title}")
                else:
                    lines.append(f"    └── {downstream_node.id}: {downstream_node.title}")

            if len(indirect_downstream) > shown_count:
                remaining = len(indirect_downstream) - shown_count
                lines.append(f"    ... and {remaining} more")
            lines.append("")
        else:
            lines.append("INDIRECT (depth 2+): None")
            lines.append("")

        # Affected files
        lines.append("AFFECTED FILES:")
        for file_path in sorted(affected_files):
            lines.append(f"  • {file_path}")
        lines.append("")

        # Suggested actions
        lines.append("SUGGESTED ACTIONS:")
        if direct_downstream:
            lines.append(f"  1. Review {len(direct_downstream)} direct downstream node(s) for consistency")
            for i, downstream_node in enumerate(direct_downstream, start=2):
                lines.append(f"  {i}. Run contextgit confirm {downstream_node.id} after review")
        else:
            lines.append("  • No downstream dependencies to review")

        return '\n'.join(lines)

    def _format_json(
        self,
        node,
        direct_downstream,
        indirect_downstream,
        affected_files
    ) -> str:
        """Format output as JSON.

        Args:
            node: The target node being analyzed
            direct_downstream: List of direct downstream nodes
            indirect_downstream: List of indirect downstream nodes
            affected_files: Set of affected file paths

        Returns:
            JSON-formatted string
        """
        data = {
            "requirement_id": node.id,
            "title": node.title,
            "type": node.type.value,
            "direct_downstream": [
                {
                    "id": n.id,
                    "title": n.title,
                    "type": n.type.value,
                    "file": n.file
                }
                for n in direct_downstream
            ],
            "indirect_downstream": [
                {
                    "id": n.id,
                    "title": n.title,
                    "type": n.type.value,
                    "file": n.file
                }
                for n in indirect_downstream
            ],
            "affected_files": sorted(list(affected_files)),
            "suggested_actions": []
        }

        # Add suggested actions
        if direct_downstream:
            for downstream_node in direct_downstream:
                data["suggested_actions"].append(f"Review {downstream_node.id} for consistency")
                data["suggested_actions"].append(f"Run contextgit confirm {downstream_node.id} after review")

        return json.dumps(data, indent=2)

    def _format_checklist(
        self,
        node,
        direct_downstream,
        indirect_downstream
    ) -> str:
        """Format output as a checklist (for PRs).

        Args:
            node: The target node being analyzed
            direct_downstream: List of direct downstream nodes
            indirect_downstream: List of indirect downstream nodes

        Returns:
            Markdown checklist string
        """
        lines = []
        lines.append(f"## Impact of changes to {node.id}")
        lines.append("")

        # Review checklist
        if direct_downstream or indirect_downstream:
            lines.append("### Review checklist")
            for downstream_node in direct_downstream:
                lines.append(f"- [ ] {downstream_node.id}: {downstream_node.title}")
            for downstream_node in indirect_downstream:
                lines.append(f"- [ ] {downstream_node.id}: {downstream_node.title} (indirect)")
            lines.append("")

        # After review
        if direct_downstream:
            lines.append("### After review")
            for downstream_node in direct_downstream:
                lines.append(f"- [ ] `contextgit confirm {downstream_node.id}`")
            if indirect_downstream:
                for downstream_node in indirect_downstream:
                    lines.append(f"- [ ] `contextgit confirm {downstream_node.id}` (if affected)")
        elif indirect_downstream:
            lines.append("### After review")
            for downstream_node in indirect_downstream:
                lines.append(f"- [ ] `contextgit confirm {downstream_node.id}`")
        else:
            lines.append("### No downstream dependencies")

        return '\n'.join(lines)


# CLI command function (can be imported by main CLI module)
def impact_command(
    requirement_id: str,
    depth: int = 2,
    format: str = "tree",
):
    """Analyze the impact of changing a requirement.

    Args:
        requirement_id: ID to analyze (e.g., SR-006)
        depth: Traversal depth (default 2)
        format: Output format (tree, json, checklist)

    This function is designed to be called from a Typer CLI command.
    It creates the necessary dependencies and calls the handler.
    """
    from contextgit.infra.filesystem import FileSystem
    from contextgit.infra.yaml_io import YAMLSerializer
    from contextgit.infra.output import OutputFormatter

    fs = FileSystem()
    yaml = YAMLSerializer()
    formatter = OutputFormatter()
    handler = ImpactHandler(fs, yaml, formatter)

    try:
        result = handler.handle(requirement_id=requirement_id, depth=depth, format=format)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=__import__('sys').stderr)
        raise SystemExit(1)
