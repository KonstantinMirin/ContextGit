"""Handler for contextgit validate command.

contextgit:
  id: C-113
  type: code
  title: "Validate Handler - Metadata Validation"
  status: active
  upstream: [SR-012]
  tags: [cli, validation, error-detection]

This module implements the ValidateHandler, which checks metadata validity
without modifying the index. It performs comprehensive validation including:
- Self-references (nodes referencing themselves)
- Missing targets (references to non-existent nodes)
- Duplicate IDs (same explicit ID used multiple times)
- Orphan nodes (nodes without proper upstream/downstream)
- Circular dependencies (cross-file cycles)
- Parse errors (malformed YAML/metadata)
"""

import json
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict
import typer

from contextgit.handlers.base import BaseHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.domain.linking.engine import LinkingEngine
from contextgit.scanners import get_scanner, get_supported_extensions
from contextgit.exceptions import (
    SelfReferentialError,
    CircularDependencyError,
    InvalidMetadataError,
)


class IssueSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A validation issue found during scanning.

    Attributes:
        severity: Issue severity level
        code: Issue code (e.g., SELF_REFERENCE, MISSING_TARGET)
        message: Human-readable description
        file: File where issue was found
        line: Line number (if available)
        suggestion: Suggested fix
    """

    severity: IssueSeverity
    code: str
    message: str
    file: str
    line: Optional[int]
    suggestion: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "suggestion": self.suggestion,
        }


class ValidateHandler(BaseHandler):
    """Handler for contextgit validate command.

    The validate command checks metadata validity without modifying the index.
    It scans files and reports validation issues including:
    1. Self-references (node referencing itself)
    2. Missing targets (references to non-existent nodes)
    3. Duplicate IDs (same explicit ID used multiple times)
    4. Orphan nodes (missing upstream/downstream)
    5. Circular dependencies (cross-file cycles)
    6. Parse errors (malformed metadata)
    """

    def handle(
        self,
        path: str = ".",
        recursive: bool = True,
        fix: bool = False,
        format: str = "text",
    ) -> str:
        """Validate metadata in files without modifying the index.

        Args:
            path: Path to scan (default: current directory)
            recursive: Scan recursively through subdirectories
            fix: Auto-fix fixable issues (not yet implemented)
            format: Output format (text or json)

        Returns:
            Validation results formatted according to format parameter

        Raises:
            RepoNotFoundError: If not in a contextgit repository
        """
        # Find repo root
        repo_root = self.find_repo_root()

        # Determine scan path
        if path:
            scan_path = Path(path).resolve()
        else:
            scan_path = Path(repo_root)

        # Find all supported files
        files = []
        supported_extensions = get_supported_extensions()
        for ext in supported_extensions:
            pattern = f"*{ext}"
            files.extend(list(self.fs.walk_files(str(scan_path), pattern, recursive)))

        # Initialize tracking structures
        issues: List[ValidationIssue] = []
        blocks_found = 0
        node_ids: Dict[str, tuple[str, int]] = {}  # id -> (file, line)
        node_metadata: Dict[str, tuple[List[str], List[str]]] = (
            {}
        )  # id -> (upstream, downstream)

        # Phase 1: Scan files and extract metadata
        for file_path in files:
            # Calculate relative path from repo root
            try:
                rel_path = str(Path(file_path).relative_to(repo_root))
            except ValueError:
                rel_path = str(file_path)

            # Get scanner
            scanner = get_scanner(Path(file_path))
            if not scanner:
                continue

            # Extract metadata
            try:
                extracted_blocks = scanner.extract_metadata(Path(file_path))
            except InvalidMetadataError as e:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="PARSE_ERROR",
                        message=f"Malformed metadata: {e}",
                        file=rel_path,
                        line=None,
                        suggestion="Fix YAML syntax in metadata block",
                    )
                )
                continue
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="PARSE_ERROR",
                        message=f"Unexpected error: {e}",
                        file=rel_path,
                        line=None,
                        suggestion="Check file format and metadata syntax",
                    )
                )
                continue

            # Process extracted blocks
            for extracted in extracted_blocks:
                blocks_found += 1

                # Skip auto-generated IDs for validation
                if extracted.id == "auto" or not extracted.id:
                    continue

                node_id = extracted.id

                # Check for duplicate IDs
                if node_id in node_ids:
                    prev_file, prev_line = node_ids[node_id]
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="DUPLICATE_ID",
                            message=f"Duplicate ID '{node_id}' (also in {prev_file}:{prev_line})",
                            file=rel_path,
                            line=extracted.line_number,
                            suggestion=f"Use unique ID or set to 'auto'",
                        )
                    )
                else:
                    node_ids[node_id] = (rel_path, extracted.line_number)

                # Store metadata for link validation
                node_metadata[node_id] = (extracted.upstream, extracted.downstream)

                # Check for self-references in upstream
                if node_id in extracted.upstream:
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="SELF_REFERENCE",
                            message=f"Node {node_id} references itself in upstream",
                            file=rel_path,
                            line=extracted.line_number,
                            suggestion=f"Remove {node_id} from upstream list",
                        )
                    )

                # Check for self-references in downstream
                if node_id in extracted.downstream:
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="SELF_REFERENCE",
                            message=f"Node {node_id} references itself in downstream",
                            file=rel_path,
                            line=extracted.line_number,
                            suggestion=f"Remove {node_id} from downstream list",
                        )
                    )

        # Phase 2: Validate references
        for node_id, (upstream, downstream) in node_metadata.items():
            file, line = node_ids[node_id]

            # Check upstream references
            for ref_id in upstream:
                if ref_id not in node_ids:
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="MISSING_TARGET",
                            message=f"Reference to unknown node: {ref_id} (in upstream of {node_id})",
                            file=file,
                            line=line,
                            suggestion=f"Create node {ref_id} or fix the reference",
                        )
                    )

            # Check downstream references
            for ref_id in downstream:
                if ref_id not in node_ids:
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            code="MISSING_TARGET",
                            message=f"Reference to unknown node: {ref_id} (in downstream of {node_id})",
                            file=file,
                            line=line,
                            suggestion=f"Create node {ref_id} or fix the reference",
                        )
                    )

        # Phase 3: Build temporary graph for cycle detection
        # Build adjacency list
        adjacency: Dict[str, List[str]] = {}
        for node_id, (upstream, downstream) in node_metadata.items():
            if node_id not in adjacency:
                adjacency[node_id] = []

            # Add edges from upstream to this node
            for upstream_id in upstream:
                if upstream_id in node_ids:
                    if upstream_id not in adjacency:
                        adjacency[upstream_id] = []
                    adjacency[upstream_id].append(node_id)

            # Add edges from this node to downstream
            for downstream_id in downstream:
                if downstream_id in node_ids:
                    adjacency[node_id].append(downstream_id)

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        cycles_found = []

        def find_cycles(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                if neighbor not in visited:
                    find_cycles(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]

                    # Check if cycle crosses file boundaries
                    files_in_cycle = set()
                    for nid in cycle:
                        if nid in node_ids:
                            file, _ = node_ids[nid]
                            files_in_cycle.add(file)

                    # Only report cross-file cycles
                    if len(files_in_cycle) > 1:
                        cycles_found.append(cycle)

            rec_stack.discard(node_id)

        for node_id in node_ids:
            if node_id not in visited:
                find_cycles(node_id, [])

        # Report cycles
        for cycle in cycles_found:
            cycle_str = " -> ".join(cycle)
            first_node = cycle[0]
            file, line = node_ids[first_node]
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code="CIRCULAR_DEPENDENCY",
                    message=f"Circular dependency detected: {cycle_str}",
                    file=file,
                    line=line,
                    suggestion="Break the cycle by removing one of the links",
                )
            )

        # Phase 4: Check for orphans (nodes without upstream/downstream)
        for node_id, (upstream, downstream) in node_metadata.items():
            file, line = node_ids[node_id]

            # Warning if no upstream (unless it's a business requirement)
            if not upstream:
                # We can't check node type here since we haven't built full nodes
                # So we'll make this a warning for all nodes
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        code="ORPHAN_NODE",
                        message=f"{node_id} has no upstream references",
                        file=file,
                        line=line,
                        suggestion="Add upstream reference to link requirements (unless this is a top-level business requirement)",
                    )
                )

            # Warning if no downstream (unless it's code or test)
            if not downstream:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        code="ORPHAN_NODE",
                        message=f"{node_id} has no downstream references",
                        file=file,
                        line=line,
                        suggestion="Add downstream reference to link implementations (unless this is a code or test node)",
                    )
                )

        # Sort issues by severity, then file, then line
        severity_order = {IssueSeverity.ERROR: 0, IssueSeverity.WARNING: 1, IssueSeverity.INFO: 2}
        issues.sort(key=lambda i: (severity_order[i.severity], i.file, i.line or 0))

        # Calculate summary
        error_count = sum(1 for i in issues if i.severity == IssueSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        info_count = sum(1 for i in issues if i.severity == IssueSeverity.INFO)

        # Format output
        if format == "json":
            return json.dumps(
                {
                    "files_scanned": len(files),
                    "blocks_found": blocks_found,
                    "issues": [i.to_dict() for i in issues],
                    "summary": {
                        "errors": error_count,
                        "warnings": warning_count,
                        "info": info_count,
                    },
                },
                indent=2,
            )
        else:
            return self._format_text_output(
                len(files), blocks_found, issues, error_count, warning_count, info_count
            )

    def _format_text_output(
        self,
        files_scanned: int,
        blocks_found: int,
        issues: List[ValidationIssue],
        error_count: int,
        warning_count: int,
        info_count: int,
    ) -> str:
        """Format validation results as text.

        Args:
            files_scanned: Number of files scanned
            blocks_found: Number of metadata blocks found
            issues: List of validation issues
            error_count: Number of errors
            warning_count: Number of warnings
            info_count: Number of info messages

        Returns:
            Formatted text output
        """
        lines = [
            "Validation Results",
            "=" * 60,
            f"Files scanned: {files_scanned}",
            f"Blocks found: {blocks_found}",
            "",
        ]

        if not issues:
            lines.append("✓ No issues found")
            return "\n".join(lines)

        # Group issues by severity
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        warnings = [i for i in issues if i.severity == IssueSeverity.WARNING]
        infos = [i for i in issues if i.severity == IssueSeverity.INFO]

        # Display errors
        if errors:
            lines.append(f"ERRORS ({len(errors)}):")
            for issue in errors:
                location = f"{issue.file}"
                if issue.line:
                    location += f":{issue.line}"
                lines.append(f"  ✗ [{issue.code}] {location} - {issue.message}")
                lines.append(f"    Suggestion: {issue.suggestion}")
                lines.append("")

        # Display warnings
        if warnings:
            lines.append(f"WARNINGS ({len(warnings)}):")
            for issue in warnings:
                location = f"{issue.file}"
                if issue.line:
                    location += f":{issue.line}"
                lines.append(f"  ⚠ [{issue.code}] {location} - {issue.message}")
                lines.append(f"    Suggestion: {issue.suggestion}")
                lines.append("")

        # Display info
        if infos:
            lines.append(f"INFO ({len(infos)}):")
            for issue in infos:
                location = f"{issue.file}"
                if issue.line:
                    location += f":{issue.line}"
                lines.append(f"  ℹ [{issue.code}] {location} - {issue.message}")
                lines.append(f"    Suggestion: {issue.suggestion}")
                lines.append("")

        # Summary
        lines.append(f"Summary: {error_count} errors, {warning_count} warnings, {info_count} info")

        return "\n".join(lines)


def validate_command(
    path: str = typer.Argument(
        ".", help="Path to scan (default: current directory)"
    ),
    recursive: bool = typer.Option(
        True, "-r", "--recursive", help="Scan recursively through subdirectories"
    ),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix fixable issues (not yet implemented)"),
    format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Validate metadata without modifying the index.

    Checks for:
    - Self-references (nodes referencing themselves)
    - Missing targets (references to non-existent nodes)
    - Duplicate IDs (same explicit ID used multiple times)
    - Orphan nodes (nodes without proper upstream/downstream)
    - Circular dependencies (cross-file cycles)
    - Parse errors (malformed YAML/metadata)

    Exit codes:
        0 - No errors found
        1 - Errors found (warnings don't cause non-zero exit)

    Examples:
        # Validate current directory recursively
        contextgit validate

        # Validate specific directory
        contextgit validate docs/

        # Get JSON output for CI integration
        contextgit validate --format json

        # Non-recursive scan
        contextgit validate --no-recursive
    """
    fs = FileSystem()
    yaml = YAMLSerializer()
    formatter = OutputFormatter()
    handler = ValidateHandler(fs, yaml, formatter)

    try:
        result = handler.handle(path=path, recursive=recursive, fix=fix, format=format)
        typer.echo(result)

        # Parse result to check for errors
        # If format is JSON, check the summary
        if format == "json":
            import json as json_module

            data = json_module.loads(result)
            if data["summary"]["errors"] > 0:
                raise typer.Exit(code=1)
        else:
            # For text format, check if "ERRORS" appears in output
            if "ERRORS (" in result and not result.startswith("✓ No issues found"):
                raise typer.Exit(code=1)

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
