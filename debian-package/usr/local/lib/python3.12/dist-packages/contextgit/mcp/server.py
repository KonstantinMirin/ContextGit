"""MCP server implementation for contextgit.

contextgit:
  id: C-123
  type: code
  title: "MCP Server - Model Context Protocol Integration"
  status: active
  upstream: [SR-012]
  tags: [mcp, llm-integration, server]

This module implements a Model Context Protocol server that exposes
contextgit functionality to LLMs for real-time requirements querying.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server import Server
    from mcp.types import Tool, Resource, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Define stub classes for type hints when MCP is not available
    class Server:  # type: ignore
        pass
    class Tool:  # type: ignore
        pass
    class Resource:  # type: ignore
        pass
    class TextContent:  # type: ignore
        pass

from contextgit.handlers.extract_handler import ExtractHandler
from contextgit.handlers.relevant_handler import RelevantHandler
from contextgit.handlers.status_handler import StatusHandler
from contextgit.handlers.impact_handler import ImpactHandler
from contextgit.handlers.scan_handler import ScanHandler
from contextgit.handlers.confirm_handler import ConfirmHandler
from contextgit.handlers.next_id_handler import NextIdHandler
from contextgit.handlers.link_handler import LinkHandler
from contextgit.handlers.hooks_handler import HooksHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.domain.index.manager import IndexManager
from contextgit.exceptions import RepoNotFoundError, NodeNotFoundError


class ContextGitMCPServer:
    """MCP Server for contextgit operations.

    Provides tools and resources for LLMs to query requirements in real-time.
    """

    def __init__(self, repo_root: Optional[str] = None):
        """Initialize the MCP server.

        Args:
            repo_root: Optional repository root path. If None, will detect from CWD.
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP library is not installed. "
                "Install it with: pip install 'contextgit[mcp]'"
            )

        self.server = Server("contextgit")
        self.repo_root = repo_root

        # Initialize infrastructure components
        self.fs = FileSystem()
        self.yaml = YAMLSerializer()
        self.formatter = OutputFormatter()

        # Register tools and resources
        self._register_tools()
        self._register_resources()

    def _find_repo_root(self) -> str:
        """Find repository root.

        Returns:
            Absolute path to repository root

        Raises:
            RepoNotFoundError: If not in a contextgit repository
        """
        if self.repo_root:
            return self.repo_root

        try:
            return self.fs.find_repo_root(str(Path.cwd()))
        except FileNotFoundError:
            raise RepoNotFoundError(
                "Not in a contextgit repository. Run 'contextgit init' first."
            )

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="contextgit_relevant_for_file",
                    description="Get requirements relevant to a source file by identifying nodes that reference the file and traversing their upstream links",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the source file"
                            },
                            "depth": {
                                "type": "integer",
                                "description": "Maximum traversal depth (default: 3)",
                                "default": 3
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="contextgit_extract",
                    description="Extract full context snippet for a requirement from its source file. Returns the precise text content.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "requirement_id": {
                                "type": "string",
                                "description": "Requirement ID to extract (e.g., SR-010, BR-002)"
                            }
                        },
                        "required": ["requirement_id"]
                    }
                ),
                Tool(
                    name="contextgit_status",
                    description="Get project health status including node counts, link status, and optionally stale links or orphan nodes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "stale_only": {
                                "type": "boolean",
                                "description": "Show only stale links",
                                "default": False
                            },
                            "orphans_only": {
                                "type": "boolean",
                                "description": "Show only orphan nodes",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="contextgit_impact_analysis",
                    description="Analyze the downstream impact of changing a requirement. Shows all affected nodes and files.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "requirement_id": {
                                "type": "string",
                                "description": "Requirement ID to analyze (e.g., SR-006)"
                            },
                            "depth": {
                                "type": "integer",
                                "description": "Traversal depth (default: 2)",
                                "default": 2
                            }
                        },
                        "required": ["requirement_id"]
                    }
                ),
                Tool(
                    name="contextgit_search",
                    description="Search requirements by keyword in titles. Optionally filter by node types.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (searches in node titles)"
                            },
                            "types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by node types (e.g., ['business', 'system', 'architecture'])"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                # Mutation tools
                Tool(
                    name="contextgit_scan",
                    description="Scan files for contextgit metadata and update the index. Use after modifying requirement files.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Paths to scan (files or directories)"
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Scan directories recursively (default: true)",
                                "default": True
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "Preview changes without modifying index (default: false)",
                                "default": False
                            }
                        },
                        "required": ["paths"]
                    }
                ),
                Tool(
                    name="contextgit_confirm",
                    description="Mark a requirement as synchronized after reviewing and updating downstream items. Clears stale status on all incoming links.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "requirement_id": {
                                "type": "string",
                                "description": "Requirement ID to confirm (e.g., SR-015)"
                            }
                        },
                        "required": ["requirement_id"]
                    }
                ),
                Tool(
                    name="contextgit_next_id",
                    description="Generate the next available ID for a given node type. Use when creating new requirements.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Node type: business, system, architecture, code, test, or decision",
                                "enum": ["business", "system", "architecture", "code", "test", "decision"]
                            }
                        },
                        "required": ["type"]
                    }
                ),
                Tool(
                    name="contextgit_link",
                    description="Create a manual traceability link between two nodes.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "from_id": {
                                "type": "string",
                                "description": "Source node ID (upstream)"
                            },
                            "to_id": {
                                "type": "string",
                                "description": "Target node ID (downstream)"
                            },
                            "relation_type": {
                                "type": "string",
                                "description": "Type of relationship",
                                "enum": ["refines", "implements", "tests", "derived_from", "depends_on"]
                            }
                        },
                        "required": ["from_id", "to_id", "relation_type"]
                    }
                ),
                Tool(
                    name="contextgit_hooks",
                    description="Manage git hooks for contextgit integration. Install hooks to automatically scan on commit.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "Action to perform",
                                "enum": ["install", "uninstall", "status"]
                            },
                            "hooks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific hooks to install/uninstall (default: all)",
                                "default": ["pre-commit", "post-merge"]
                            }
                        },
                        "required": ["action"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                if name == "contextgit_relevant_for_file":
                    return await self._tool_relevant_for_file(
                        arguments["file_path"],
                        arguments.get("depth", 3)
                    )
                elif name == "contextgit_extract":
                    return await self._tool_extract(arguments["requirement_id"])
                elif name == "contextgit_status":
                    return await self._tool_status(
                        arguments.get("stale_only", False),
                        arguments.get("orphans_only", False)
                    )
                elif name == "contextgit_impact_analysis":
                    return await self._tool_impact_analysis(
                        arguments["requirement_id"],
                        arguments.get("depth", 2)
                    )
                elif name == "contextgit_search":
                    return await self._tool_search(
                        arguments["query"],
                        arguments.get("types")
                    )
                # Mutation tools
                elif name == "contextgit_scan":
                    return await self._tool_scan(
                        arguments["paths"],
                        arguments.get("recursive", True),
                        arguments.get("dry_run", False)
                    )
                elif name == "contextgit_confirm":
                    return await self._tool_confirm(arguments["requirement_id"])
                elif name == "contextgit_next_id":
                    return await self._tool_next_id(arguments["type"])
                elif name == "contextgit_link":
                    return await self._tool_link(
                        arguments["from_id"],
                        arguments["to_id"],
                        arguments["relation_type"]
                    )
                elif name == "contextgit_hooks":
                    return await self._tool_hooks(
                        arguments["action"],
                        arguments.get("hooks", ["pre-commit", "post-merge"])
                    )
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _register_resources(self) -> None:
        """Register MCP resources."""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri="contextgit://index",
                    name="Requirements Index",
                    description="Full requirements index with all nodes and links",
                    mimeType="application/json"
                ),
                Resource(
                    uri="contextgit://llm-instructions",
                    name="LLM Integration Instructions",
                    description="Instructions for LLMs on how to use contextgit effectively",
                    mimeType="text/markdown"
                )
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Handle resource reads."""
            try:
                if uri == "contextgit://index":
                    return await self._resource_index()
                elif uri == "contextgit://llm-instructions":
                    return await self._resource_llm_instructions()
                else:
                    return json.dumps({"error": f"Unknown resource: {uri}"})
            except Exception as e:
                return json.dumps({"error": str(e)})

    # Tool implementations

    async def _tool_relevant_for_file(self, file_path: str, depth: int) -> List[TextContent]:
        """Implement relevant_for_file tool."""
        handler = RelevantHandler(self.fs, self.yaml, self.formatter)
        try:
            result = handler.handle(file_path=file_path, depth=depth, format="json")
            return [TextContent(type="text", text=result)]
        except Exception as e:
            error_msg = json.dumps({"error": str(e)})
            return [TextContent(type="text", text=error_msg)]

    async def _tool_extract(self, requirement_id: str) -> List[TextContent]:
        """Implement extract tool."""
        handler = ExtractHandler(self.fs, self.yaml, self.formatter)
        try:
            result = handler.handle(node_id=requirement_id, format="json")
            return [TextContent(type="text", text=result)]
        except NodeNotFoundError as e:
            error_msg = json.dumps({"error": f"Node not found: {str(e)}"})
            return [TextContent(type="text", text=error_msg)]
        except Exception as e:
            error_msg = json.dumps({"error": str(e)})
            return [TextContent(type="text", text=error_msg)]

    async def _tool_status(self, stale_only: bool, orphans_only: bool) -> List[TextContent]:
        """Implement status tool."""
        handler = StatusHandler(self.fs, self.yaml, self.formatter)
        try:
            result = handler.handle(stale=stale_only, orphans=orphans_only, format="json")
            return [TextContent(type="text", text=result)]
        except Exception as e:
            error_msg = json.dumps({"error": str(e)})
            return [TextContent(type="text", text=error_msg)]

    async def _tool_impact_analysis(self, requirement_id: str, depth: int) -> List[TextContent]:
        """Implement impact_analysis tool."""
        handler = ImpactHandler(self.fs, self.yaml, self.formatter)
        try:
            result = handler.handle(requirement_id=requirement_id, depth=depth, format="json")
            return [TextContent(type="text", text=result)]
        except NodeNotFoundError as e:
            error_msg = json.dumps({"error": f"Node not found: {str(e)}"})
            return [TextContent(type="text", text=error_msg)]
        except Exception as e:
            error_msg = json.dumps({"error": str(e)})
            return [TextContent(type="text", text=error_msg)]

    async def _tool_search(self, query: str, types: Optional[List[str]]) -> List[TextContent]:
        """Implement search tool."""
        try:
            repo_root = self._find_repo_root()
            index_mgr = IndexManager(self.fs, self.yaml, repo_root)
            index = index_mgr.load_index()

            # Search in titles
            results = []
            query_lower = query.lower()

            for node in index.nodes.values():
                # Filter by type if specified
                if types and node.type.value not in types:
                    continue

                # Simple keyword matching in title
                title_lower = node.title.lower()
                if query_lower in title_lower:
                    # Calculate simple match score
                    match_score = 1.0 if query_lower == title_lower else 0.5
                    results.append({
                        "id": node.id,
                        "type": node.type.value,
                        "title": node.title,
                        "file": node.file,
                        "match_score": match_score
                    })

            # Sort by match score
            results.sort(key=lambda x: x["match_score"], reverse=True)

            response = {
                "query": query,
                "filters": {"types": types} if types else {},
                "results": results,
                "total_matches": len(results)
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except Exception as e:
            error_msg = json.dumps({"error": str(e)})
            return [TextContent(type="text", text=error_msg)]

    # Mutation tool implementations

    async def _tool_scan(
        self, paths: List[str], recursive: bool, dry_run: bool
    ) -> List[TextContent]:
        """Implement scan mutation tool.

        Scans files for contextgit metadata and updates the index.
        """
        handler = ScanHandler(self.fs, self.yaml, self.formatter)
        try:
            # Scan each path
            total_scanned = 0
            total_added = 0
            total_updated = 0
            all_errors = []

            for path in paths:
                result = handler.handle(
                    path=path,
                    recursive=recursive,
                    dry_run=dry_run,
                    format="json"
                )
                # Parse the JSON result
                result_data = json.loads(result)
                total_scanned += result_data.get("files_scanned", 0)
                total_added += result_data.get("nodes_added", 0)
                total_updated += result_data.get("nodes_updated", 0)
                if result_data.get("errors"):
                    all_errors.extend(result_data["errors"])

            response = {
                "success": True,
                "files_scanned": total_scanned,
                "nodes_added": total_added,
                "nodes_updated": total_updated,
                "dry_run": dry_run,
                "errors": all_errors
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except Exception as e:
            error_msg = json.dumps({"error": str(e), "success": False})
            return [TextContent(type="text", text=error_msg)]

    async def _tool_confirm(self, requirement_id: str) -> List[TextContent]:
        """Implement confirm mutation tool.

        Marks a requirement as synchronized after reviewing downstream items.
        """
        handler = ConfirmHandler(self.fs, self.yaml, self.formatter)
        try:
            result = handler.handle(node_id=requirement_id, format="json")
            # Parse and enhance the response
            result_data = json.loads(result)
            response = {
                "success": True,
                "confirmed": True,
                "requirement_id": requirement_id,
                "links_updated": result_data.get("links_updated", 0),
                "message": f"Requirement {requirement_id} marked as synchronized"
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except NodeNotFoundError as e:
            error_msg = json.dumps({
                "success": False,
                "confirmed": False,
                "error": f"Node not found: {str(e)}"
            })
            return [TextContent(type="text", text=error_msg)]
        except Exception as e:
            error_msg = json.dumps({
                "success": False,
                "confirmed": False,
                "error": str(e)
            })
            return [TextContent(type="text", text=error_msg)]

    async def _tool_next_id(self, node_type: str) -> List[TextContent]:
        """Implement next_id mutation tool.

        Generates the next available ID for a given node type.
        """
        handler = NextIdHandler(self.fs, self.yaml, self.formatter)
        try:
            result = handler.handle(node_type=node_type, format="json")
            # Parse and enhance the response
            result_data = json.loads(result)
            response = {
                "success": True,
                "type": node_type,
                "next_id": result_data.get("id", result_data.get("next_id")),
                "message": f"Next available ID for type '{node_type}'"
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except Exception as e:
            error_msg = json.dumps({
                "success": False,
                "error": str(e)
            })
            return [TextContent(type="text", text=error_msg)]

    async def _tool_link(
        self, from_id: str, to_id: str, relation_type: str
    ) -> List[TextContent]:
        """Implement link mutation tool.

        Creates a manual traceability link between two nodes.
        """
        handler = LinkHandler(self.fs, self.yaml, self.formatter)
        try:
            result = handler.handle(
                from_id=from_id,
                to_id=to_id,
                relation_type=relation_type,
                format="json"
            )
            # Parse and enhance the response
            result_data = json.loads(result)
            response = {
                "success": True,
                "created": True,
                "from_id": from_id,
                "to_id": to_id,
                "relation_type": relation_type,
                "message": f"Link created: {from_id} --[{relation_type}]--> {to_id}"
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except NodeNotFoundError as e:
            error_msg = json.dumps({
                "success": False,
                "created": False,
                "error": f"Node not found: {str(e)}"
            })
            return [TextContent(type="text", text=error_msg)]
        except Exception as e:
            error_msg = json.dumps({
                "success": False,
                "created": False,
                "error": str(e)
            })
            return [TextContent(type="text", text=error_msg)]

    async def _tool_hooks(
        self, action: str, hooks: List[str]
    ) -> List[TextContent]:
        """Implement hooks mutation tool.

        Manages git hooks for contextgit integration.
        """
        handler = HooksHandler(self.fs, self.yaml, self.formatter)
        try:
            if action == "install":
                # Map hooks list to install parameters
                pre_commit = "pre-commit" in hooks
                post_merge = "post-merge" in hooks
                pre_push = "pre-push" in hooks
                result = handler.install(
                    pre_commit=pre_commit,
                    post_merge=post_merge,
                    pre_push=pre_push,
                    format="json"
                )
            elif action == "uninstall":
                result = handler.uninstall(format="json")
            elif action == "status":
                result = handler.status(format="json")
            else:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": f"Unknown action: {action}. Use 'install', 'uninstall', or 'status'"
                }))]

            # Parse and enhance the response
            result_data = json.loads(result)
            response = {
                "success": True,
                "action": action,
                "hooks": hooks if action == "install" else result_data.get("hooks", result_data.get("removed", [])),
                "details": result_data
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except Exception as e:
            error_msg = json.dumps({
                "success": False,
                "action": action,
                "error": str(e)
            })
            return [TextContent(type="text", text=error_msg)]

    # Resource implementations

    async def _resource_index(self) -> str:
        """Implement index resource."""
        try:
            repo_root = self._find_repo_root()
            index_mgr = IndexManager(self.fs, self.yaml, repo_root)
            index = index_mgr.load_index()

            # Convert index to JSON
            nodes = [
                {
                    "id": node.id,
                    "type": node.type.value,
                    "title": node.title,
                    "file": node.file,
                    "status": node.status.value
                }
                for node in index.nodes.values()
            ]

            links = [
                {
                    "from_id": link.from_id,
                    "to_id": link.to_id,
                    "relation_type": link.relation_type.value,
                    "sync_status": link.sync_status.value
                }
                for link in index.links
            ]

            response = {
                "nodes": nodes,
                "links": links,
                "total_nodes": len(nodes),
                "total_links": len(links)
            }

            return json.dumps(response, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def _resource_llm_instructions(self) -> str:
        """Implement llm-instructions resource."""
        instructions = """# ContextGit LLM Integration Instructions

## Overview

ContextGit is a requirements traceability tool for LLM-assisted development.
It tracks relationships from business needs → system specs → architecture → code → tests.

## Core Concepts

- **Nodes**: Requirements/context items with unique IDs (e.g., BR-001, SR-010)
- **Links**: Traceability relationships between nodes
- **Index**: Central YAML file tracking all nodes and links
- **Staleness**: Detected when upstream requirements change via checksums

## MCP Tools Available

### 1. contextgit_relevant_for_file
Find requirements relevant to a source file.

**Use when**: You need to understand what requirements affect a specific file.

**Example**:
```json
{
  "file_path": "src/api.py",
  "depth": 3
}
```

### 2. contextgit_extract
Extract full context for a requirement.

**Use when**: You need the complete text of a requirement.

**Example**:
```json
{
  "requirement_id": "SR-010"
}
```

### 3. contextgit_status
Get project health status.

**Use when**: You want to see overall project state or find stale links.

**Example**:
```json
{
  "stale_only": true
}
```

### 4. contextgit_impact_analysis
Analyze impact of changing a requirement.

**Use when**: Before modifying a requirement, check what will be affected.

**Example**:
```json
{
  "requirement_id": "SR-006",
  "depth": 2
}
```

### 5. contextgit_search
Search requirements by keyword.

**Use when**: Looking for specific requirements by topic.

**Example**:
```json
{
  "query": "authentication",
  "types": ["system", "architecture"]
}
```

## Mutation Tools (Write Operations)

### 6. contextgit_scan
Scan files for contextgit metadata and update the index.

**Use when**: After modifying requirement files or adding new requirements.

**Example**:
```json
{
  "paths": ["docs/", "src/"],
  "recursive": true,
  "dry_run": false
}
```

### 7. contextgit_confirm
Mark a requirement as synchronized after reviewing downstream items.

**Use when**: After updating a downstream requirement to address upstream changes.

**Example**:
```json
{
  "requirement_id": "SR-015"
}
```

### 8. contextgit_next_id
Generate the next available ID for a given node type.

**Use when**: Creating new requirements with proper ID sequencing.

**Example**:
```json
{
  "type": "code"
}
```

**Returns**: `{"next_id": "C-034"}`

### 9. contextgit_link
Create a manual traceability link between two nodes.

**Use when**: Establishing relationships between requirements that aren't auto-detected.

**Example**:
```json
{
  "from_id": "SR-015",
  "to_id": "C-025",
  "relation_type": "implements"
}
```

### 10. contextgit_hooks
Manage git hooks for contextgit integration.

**Use when**: Setting up automatic scanning on commit/merge.

**Example**:
```json
{
  "action": "install",
  "hooks": ["pre-commit", "post-merge"]
}
```

## MCP Resources Available

### 1. contextgit://index
Full requirements index with all nodes and links.

**Use when**: You need a complete view of all requirements.

### 2. contextgit://llm-instructions
This document - instructions for using contextgit.

## Recommended Workflows

### Implementing a Feature (Full MCP Workflow)

1. Use `contextgit_search` to find relevant requirements
2. Use `contextgit_extract` to get full context for each requirement
3. Use `contextgit_next_id` to get the next code node ID
4. Implement the feature with metadata annotation
5. Use `contextgit_scan` to update the index
6. Use `contextgit_confirm` to mark requirements as implemented

### Creating New Requirements

1. Use `contextgit_next_id` with appropriate type (business, system, etc.)
2. Create the file with contextgit metadata using the generated ID
3. Use `contextgit_scan` to register the new requirement
4. Use `contextgit_link` if manual links are needed

### Modifying a Requirement

1. Use `contextgit_impact_analysis` to see what will be affected
2. Review all downstream nodes
3. Make the change
4. Update affected downstream items
5. Use `contextgit_scan` to update checksums
6. Use `contextgit_confirm` to mark as synchronized

### Understanding a File

1. Use `contextgit_relevant_for_file` to find related requirements
2. Use `contextgit_extract` to read each requirement
3. Understand the context and implement changes accordingly

### Finding and Fixing Stale Requirements

1. Use `contextgit_status` with `stale_only: true`
2. Review each stale link
3. Update downstream requirements as needed
4. Use `contextgit_scan` to update the index
5. Use `contextgit_confirm` to mark each fixed item as synchronized

### Setting Up Git Integration

1. Use `contextgit_hooks` with action "install"
2. Pre-commit hook will auto-scan changed files
3. Post-merge hook will scan after merges

## Best Practices

1. **Always extract context** before implementing features
2. **Check impact** before modifying requirements
3. **Document traceability** by referencing requirement IDs in code comments
4. **Keep links synchronized** by running status checks regularly
5. **Use search** to find existing requirements before creating new ones

## Node Types

- **business**: Business requirements and user stories
- **system**: System-level functional/non-functional requirements
- **architecture**: Architectural decisions and design specs
- **code**: Implementation notes and code documentation
- **test**: Test specifications and acceptance criteria
- **decision**: Architecture Decision Records (ADRs)

## Relation Types

- **refines**: Higher-level → Lower-level (e.g., BR → SR)
- **implements**: Requirement → Implementation (e.g., SR → Code)
- **tests**: Test → Implementation (e.g., Test → Code)
- **derived_from**: One requirement derived from another
- **depends_on**: Dependency relationship

## Tips for Effective Use

1. Start with `contextgit_relevant_for_file` when working on existing code
2. Use `depth` parameter to control how far to traverse relationships
3. Always check `stale_only` status before major changes
4. Use `contextgit_search` to discover related requirements
5. Run impact analysis before proposing breaking changes
"""
        return instructions

    async def run_stdio(self) -> None:
        """Run server with stdio transport."""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

    async def run_http(self, host: str = "localhost", port: int = 8080) -> None:
        """Run server with HTTP transport.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        # HTTP transport implementation would go here
        # This is optional for MVP
        raise NotImplementedError("HTTP transport not yet implemented")


def main() -> None:
    """Main entry point for MCP server."""
    if not MCP_AVAILABLE:
        print(
            "Error: MCP library is not installed.\n"
            "Install it with: pip install 'contextgit[mcp]'",
            file=sys.stderr
        )
        sys.exit(1)

    # Parse command line arguments (simple implementation)
    import argparse
    parser = argparse.ArgumentParser(description="ContextGit MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport type (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP transport (default: 8080)"
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root path (optional, will auto-detect if not provided)"
    )

    args = parser.parse_args()

    try:
        server = ContextGitMCPServer(repo_root=args.repo_root)

        if args.transport == "stdio":
            asyncio.run(server.run_stdio())
        elif args.transport == "http":
            asyncio.run(server.run_http(port=args.port))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
