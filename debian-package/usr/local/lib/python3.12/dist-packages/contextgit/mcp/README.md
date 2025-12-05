# ContextGit MCP Server

This module provides Model Context Protocol (MCP) server functionality for contextgit, enabling LLMs to query requirements in real-time.

## Installation

Install contextgit with MCP support:

```bash
pip install 'contextgit[mcp]'
```

This installs the required dependencies:
- `mcp>=0.1.0` - Model Context Protocol library
- `pydantic>=2.0.0` - Data validation and schemas

## Usage

### Starting the Server

#### Stdio Transport (for Claude Code)

```bash
# Start MCP server with stdio transport (default)
contextgit mcp-server

# Or use the dedicated script
contextgit-mcp
```

#### HTTP Transport (experimental)

```bash
# Start with HTTP transport
contextgit mcp-server --transport http --port 8080
```

### Command-Line Options

- `--transport, -t`: Transport type (`stdio` or `http`) - default: `stdio`
- `--port, -p`: Port for HTTP transport - default: `8080`
- `--host`: Host for HTTP transport - default: `localhost`
- `--repo-root, -r`: Repository root path (optional, will auto-detect if not provided)

## Available Tools

The MCP server exposes 5 tools for LLM interaction:

### 1. contextgit_relevant_for_file

Find requirements relevant to a source file.

**Parameters:**
- `file_path` (string, required): Path to the source file
- `depth` (integer, optional): Maximum traversal depth (default: 3)

**Example:**
```json
{
  "file_path": "src/api.py",
  "depth": 3
}
```

### 2. contextgit_extract

Extract full context snippet for a requirement.

**Parameters:**
- `requirement_id` (string, required): Requirement ID to extract (e.g., SR-010)

**Example:**
```json
{
  "requirement_id": "SR-010"
}
```

### 3. contextgit_status

Get project health status.

**Parameters:**
- `stale_only` (boolean, optional): Show only stale links (default: false)
- `orphans_only` (boolean, optional): Show only orphan nodes (default: false)

**Example:**
```json
{
  "stale_only": true
}
```

### 4. contextgit_impact_analysis

Analyze the downstream impact of changing a requirement.

**Parameters:**
- `requirement_id` (string, required): Requirement ID to analyze
- `depth` (integer, optional): Traversal depth (default: 2)

**Example:**
```json
{
  "requirement_id": "SR-006",
  "depth": 2
}
```

### 5. contextgit_search

Search requirements by keyword in titles.

**Parameters:**
- `query` (string, required): Search query
- `types` (array of strings, optional): Filter by node types

**Example:**
```json
{
  "query": "authentication",
  "types": ["system", "architecture"]
}
```

## Available Resources

The MCP server provides 2 resources:

### 1. contextgit://index

Full requirements index with all nodes and links in JSON format.

### 2. contextgit://llm-instructions

Comprehensive instructions for LLMs on how to use contextgit effectively.

## Integration with Claude Code

To use this MCP server with Claude Code, add it to your MCP configuration:

```json
{
  "mcpServers": {
    "contextgit": {
      "command": "contextgit-mcp",
      "args": [],
      "cwd": "/path/to/your/project"
    }
  }
}
```

Claude Code will automatically start the MCP server and use it to query requirements during conversations.

## Architecture

The MCP server is built on top of existing contextgit handlers:

- **ExtractHandler**: Provides requirement extraction functionality
- **RelevantHandler**: Finds requirements relevant to files
- **StatusHandler**: Reports project health
- **ImpactHandler**: Analyzes change impact
- **IndexManager**: Accesses the requirements index

All responses are returned as JSON for easy parsing by LLMs.

## Error Handling

The server gracefully handles errors:

- **Missing MCP library**: Clear error message with installation instructions
- **Repository not found**: Error if not in a contextgit repository
- **Node not found**: JSON error response when requirement ID doesn't exist
- **Invalid parameters**: JSON error response with details

## Development

To work on the MCP server module:

1. Install development dependencies:
   ```bash
   pip install -e '.[dev,mcp]'
   ```

2. Run tests:
   ```bash
   pytest tests/unit/mcp/
   ```

3. Type checking:
   ```bash
   mypy contextgit/mcp/
   ```

## Schemas

Pydantic schemas are defined in `schemas.py` for type-safe responses:

- `RelevantForFileResponse`: Response for relevant_for_file tool
- `ExtractResponse`: Response for extract tool
- `StatusResponse`: Response for status tool
- `ImpactAnalysisResponse`: Response for impact_analysis tool
- `SearchResponse`: Response for search tool
- `IndexResponse`: Response for index resource

These schemas ensure consistent JSON structure across all tool responses.

## Performance

The MCP server is designed for low latency:

- Tool calls reuse existing handler logic (no additional overhead)
- Index is loaded on-demand (not cached in memory)
- Async/await support for concurrent requests
- Stdio transport has minimal latency (<10ms overhead)

## Troubleshooting

### Server won't start

```bash
# Check if MCP is installed
python -c "import mcp; print('MCP is installed')"

# Reinstall if needed
pip install 'contextgit[mcp]' --force-reinstall
```

### Not in a contextgit repository

```bash
# Initialize contextgit first
contextgit init

# Or specify repo root explicitly
contextgit mcp-server --repo-root /path/to/repo
```

### Tool calls failing

Check that you're in a valid contextgit repository with an index:

```bash
contextgit status
```

If the index is missing or corrupt, rescan:

```bash
contextgit scan docs/ --recursive
```
