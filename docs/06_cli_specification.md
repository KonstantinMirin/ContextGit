# CLI Specification

## Overview

This document provides detailed specifications for all contextgit CLI commands in the MVP. Each command includes:

- Synopsis (usage syntax)
- Description
- Arguments and options
- Input/output specifications
- Error conditions
- Examples

All commands support standard Unix conventions:
- `--help`: Display help text
- Exit code 0 on success, non-zero on error
- Error messages to stderr, normal output to stdout
- Support for both short (`-f`) and long (`--format`) flags where appropriate

---

## Global Options

These options are available for all commands:

| Option | Description |
|--------|-------------|
| `--help` | Display help text for the command |
| `--version` | Display contextgit version |

---

## Command: `contextgit init`

### Synopsis

```bash
contextgit init [OPTIONS]
```

### Description

Initialize a repository to use contextgit. Creates `.contextgit/config.yaml` and `.contextgit/requirements_index.yaml` if they don't exist.

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--force` | flag | false | Overwrite existing config and index files |
| `--interactive` / `-i` | flag | false | Prompt for configuration values |

### Behavior

1. Check if `.contextgit/` directory exists
   - If exists and `--force` not set: Error
   - If exists and `--force` set: Overwrite files
2. Create `.contextgit/` directory
3. Create `config.yaml` with default or user-provided values
4. Create empty `requirements_index.yaml` with `nodes: []` and `links: []`
5. Print success message

### Exit Codes

- 0: Success
- 1: `.contextgit/` already exists and `--force` not set
- 2: Permission denied creating directory

### Examples

**Basic initialization:**
```bash
$ contextgit init
Created .contextgit/config.yaml
Created .contextgit/requirements_index.yaml
Repository initialized for contextgit.
```

**Interactive mode:**
```bash
$ contextgit init --interactive
Repository not found. Initialize contextgit? [y/N] y
Business requirements directory [docs/01_business]:
System requirements directory [docs/02_system]:
...
Created .contextgit/config.yaml
Created .contextgit/requirements_index.yaml
Repository initialized for contextgit.
```

**Force overwrite:**
```bash
$ contextgit init --force
Warning: Overwriting existing .contextgit/ directory
Created .contextgit/config.yaml
Created .contextgit/requirements_index.yaml
Repository initialized for contextgit.
```

---

## Command: `contextgit scan`

### Synopsis

```bash
contextgit scan [PATH] [OPTIONS]
```

### Description

Scan files for contextgit metadata blocks and update the index. If PATH is a file, scans that file. If PATH is a directory, scans all Markdown files in that directory (recursively if `--recursive` is set). If PATH is omitted, scans the entire repository.

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `PATH` | No | File or directory to scan (default: repository root) |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--recursive` / `-r` | flag | false | Recursively scan subdirectories |
| `--dry-run` | flag | false | Show what would change without modifying index |
| `--format` / `-f` | string | text | Output format: `text` or `json` |

### Behavior

1. Validate PATH exists
2. Load config from `.contextgit/config.yaml`
3. Load existing index from `.contextgit/requirements_index.yaml`
4. Find all Markdown files in PATH
   - If PATH is a file: process that file
   - If PATH is a directory:
     - If `--recursive`: walk all subdirectories
     - Else: only files in PATH directory
5. For each file:
   - Parse metadata blocks (YAML frontmatter and inline comments)
   - Resolve location for each block
   - Calculate checksum of content
   - Extract upstream/downstream links
6. Update index:
   - Create new nodes or update existing nodes
   - Create new links or update existing links
   - Mark sync status based on checksum changes
7. If not `--dry-run`: save index atomically
8. Output summary

### Input

Markdown files with contextgit metadata blocks (see data model document).

### Output (Text Format)

```
Scanned 5 files
Nodes:
  Added: 3 (BR-002, SR-012, AR-030)
  Updated: 2 (SR-010, AR-020)
  Unchanged: 10
Links:
  Added: 4
  Updated: 2 (marked as upstream_changed)
Index updated: .contextgit/requirements_index.yaml
```

### Output (JSON Format)

```json
{
  "files_scanned": 5,
  "nodes": {
    "added": ["BR-002", "SR-012", "AR-030"],
    "updated": ["SR-010", "AR-020"],
    "unchanged": 10
  },
  "links": {
    "added": 4,
    "updated": 2
  },
  "index_path": ".contextgit/requirements_index.yaml"
}
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 3 | PATH not found | `Error: Path not found: {PATH}` |
| 4 | Invalid metadata in file | `Error: Invalid metadata in {FILE}:{LINE}: {REASON}` |
| 5 | Index file corrupted | `Error: Could not load index: {REASON}` |

### Examples

**Scan entire repository:**
```bash
$ contextgit scan --recursive
Scanned 23 files
Nodes: Added 5, Updated 2, Unchanged 15
Links: Added 8, Updated 1
Index updated: .contextgit/requirements_index.yaml
```

**Scan specific directory:**
```bash
$ contextgit scan docs/02_system --recursive
Scanned 3 files
Nodes: Added 0, Updated 1, Unchanged 5
Links: Added 0, Updated 0
Index updated: .contextgit/requirements_index.yaml
```

**Dry run:**
```bash
$ contextgit scan docs/ --recursive --dry-run
[DRY RUN] Would scan 15 files
[DRY RUN] Would add 3 nodes: BR-005, SR-020, AR-040
[DRY RUN] Would update 1 node: SR-010
[DRY RUN] Would add 4 links
No changes made (dry run).
```

**JSON output:**
```bash
$ contextgit scan docs/ --recursive --format json
{"files_scanned": 15, "nodes": {"added": ["BR-005", "SR-020", "AR-040"], "updated": ["SR-010"], "unchanged": 12}, "links": {"added": 4, "updated": 0}, "index_path": ".contextgit/requirements_index.yaml"}
```

---

## Command: `contextgit status`

### Synopsis

```bash
contextgit status [OPTIONS]
```

### Description

Display overall project health and traceability status.

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--orphans` | flag | false | Show only orphan nodes |
| `--stale` | flag | false | Show only stale or broken links |
| `--file` / `-F` | string | - | Filter to specific file |
| `--type` / `-t` | string | - | Filter to specific node type |
| `--format` / `-f` | string | text | Output format: `text` or `json` |

### Behavior

1. Load index
2. Calculate statistics:
   - Count nodes by type
   - Count links total, stale, broken
   - Identify orphan nodes (no upstream or no downstream)
3. Apply filters if specified
4. Output results

### Output (Text Format)

```
contextgit status:

Nodes:
  business: 5
  system: 12
  architecture: 8
  code: 23
  test: 15
  decision: 2

Links: 48

Health:
  Stale links: 3
  Broken links: 0
  Orphan nodes: 2 (no downstream)

Run 'contextgit status --stale' for details on stale links.
Run 'contextgit status --orphans' for details on orphan nodes.
```

### Output (JSON Format)

```json
{
  "nodes": {
    "business": 5,
    "system": 12,
    "architecture": 8,
    "code": 23,
    "test": 15,
    "decision": 2,
    "other": 0
  },
  "links": {
    "total": 48,
    "stale": 3,
    "broken": 0
  },
  "orphans": {
    "no_upstream": ["C-150", "C-151"],
    "no_downstream": ["SR-015", "AR-025"]
  }
}
```

### Output with `--stale` (Text Format)

```
Stale links (need review):

Upstream changed:
  BR-001 → SR-010 (last checked: 2025-12-02T18:00:00Z)
  BR-001 → SR-011 (last checked: 2025-12-02T18:00:00Z)

Downstream changed:
  SR-010 → C-120 (last checked: 2025-12-02T19:00:00Z)

Run 'contextgit confirm <ID>' to mark as synchronized.
```

### Output with `--orphans` (Text Format)

```
Orphan nodes:

No upstream:
  C-150: "Utility function for date parsing" (code)
  C-151: "Helper for JSON serialization" (code)

No downstream:
  SR-015: "System shall support async job processing" (system)
  AR-025: "Cache layer architecture" (architecture)
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 5 | Index not found or corrupted | `Error: Could not load index: {REASON}` |

### Examples

**Basic status:**
```bash
$ contextgit status
contextgit status:
Nodes: business=5, system=12, architecture=8, code=23, test=15
Links: 48
Health: Stale=3, Broken=0, Orphans=2
```

**Show stale links:**
```bash
$ contextgit status --stale
Stale links (need review):
  BR-001 → SR-010 (upstream_changed)
  BR-001 → SR-011 (upstream_changed)
  SR-010 → C-120 (downstream_changed)
```

**Filter by type:**
```bash
$ contextgit status --type system
System requirements: 12 nodes
Upstream links: 15
Downstream links: 20
Stale: 2
```

**JSON output:**
```bash
$ contextgit status --format json | jq .
{
  "nodes": { ... },
  "links": { ... },
  "orphans": { ... }
}
```

---

## Command: `contextgit show`

### Synopsis

```bash
contextgit show <ID> [OPTIONS]
```

### Description

Display detailed information about a specific node, including metadata, upstream links, and downstream links.

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `ID` | Yes | Node ID to display (e.g., "SR-010") |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` / `-f` | string | text | Output format: `text` or `json` |
| `--graph` | flag | false | Display a simple text-based graph |

### Behavior

1. Load index
2. Find node by ID
3. Find all upstream links (where this node is `to`)
4. Find all downstream links (where this node is `from`)
5. Output node details and links

### Output (Text Format)

```
Node: SR-010

Type: system
Title: System shall expose job execution logs via API
File: docs/02_system/logging_api.md
Location: heading → ["System Design – Logging", "3.1 Logging API"]
Status: active
Last updated: 2025-12-02T18:00:00Z
Checksum: def456789abc...
Tags: feature:observability, api:rest

Upstream (1):
  BR-001: "Scheduled jobs must be observable" [refines] (ok)

Downstream (2):
  AR-020: "REST API design for logging" [refines] (ok)
  C-120: "LoggingAPIHandler class" [implements] (upstream_changed)
```

### Output (JSON Format)

```json
{
  "node": {
    "id": "SR-010",
    "type": "system",
    "title": "System shall expose job execution logs via API",
    "file": "docs/02_system/logging_api.md",
    "location": {
      "kind": "heading",
      "path": ["System Design – Logging", "3.1 Logging API"]
    },
    "status": "active",
    "last_updated": "2025-12-02T18:00:00Z",
    "checksum": "def456789abc...",
    "llm_generated": false,
    "tags": ["feature:observability", "api:rest"]
  },
  "upstream": [
    {
      "id": "BR-001",
      "title": "Scheduled jobs must be observable",
      "relation": "refines",
      "sync_status": "ok"
    }
  ],
  "downstream": [
    {
      "id": "AR-020",
      "title": "REST API design for logging",
      "relation": "refines",
      "sync_status": "ok"
    },
    {
      "id": "C-120",
      "title": "LoggingAPIHandler class",
      "relation": "implements",
      "sync_status": "upstream_changed"
    }
  ]
}
```

### Output with `--graph`

```
      BR-001
       (ok)
        │
        ▼
     SR-010
        │
        ├─────────┬───────────┐
        │         │           │
       (ok)  (ok)  (upstream_changed)
        │         │           │
        ▼         ▼           ▼
     AR-020    AR-021      C-120
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 3 | Node ID not found | `Error: Node not found: {ID}` |
| 5 | Index not found | `Error: Could not load index` |

### Examples

**Show node details:**
```bash
$ contextgit show SR-010
Node: SR-010
Type: system
Title: System shall expose job execution logs via API
...
```

**JSON output:**
```bash
$ contextgit show SR-010 --format json
{"node": {...}, "upstream": [...], "downstream": [...]}
```

**Graph view:**
```bash
$ contextgit show SR-010 --graph
      BR-001
        │
        ▼
     SR-010
        │
        ├─────────┬
        ▼         ▼
     AR-020    C-120
```

---

## Command: `contextgit extract`

### Synopsis

```bash
contextgit extract <ID> [OPTIONS]
```

### Description

Extract the text snippet for a specific node from its source file. This is the primary command for LLMs to get precise context.

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `ID` | Yes | Node ID to extract (e.g., "SR-010") |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` / `-f` | string | text | Output format: `text` or `json` |

### Behavior

1. Load index
2. Find node by ID
3. Read source file
4. Extract snippet using location information:
   - For heading location: extract from heading through content until next same-level heading
   - For line location: extract lines from start to end
5. Output snippet

### Output (Text Format)

```
The system shall provide a REST API endpoint `/api/logs` that returns job execution logs. The API must support:

- Filtering by job ID
- Filtering by date range
- Filtering by status (success, failure, running)
- Pagination for large result sets

### API Specification

**Endpoint**: `GET /api/logs`
...
```

### Output (JSON Format)

```json
{
  "id": "SR-010",
  "file": "docs/02_system/logging_api.md",
  "location": {
    "kind": "heading",
    "path": ["System Design – Logging", "3.1 Logging API"]
  },
  "snippet": "The system shall provide a REST API endpoint `/api/logs` that returns job execution logs. The API must support:\n\n- Filtering by job ID\n..."
}
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 3 | Node ID not found | `Error: Node not found: {ID}` |
| 3 | Source file not found | `Error: File not found: {FILE}` |
| 5 | Index not found | `Error: Could not load index` |

### Examples

**Extract snippet (text):**
```bash
$ contextgit extract SR-010
The system shall provide a REST API endpoint `/api/logs` that returns...
```

**Extract snippet (JSON):**
```bash
$ contextgit extract SR-010 --format json
{"id": "SR-010", "file": "docs/02_system/logging_api.md", "snippet": "..."}
```

**Pipe to file:**
```bash
$ contextgit extract SR-010 > /tmp/sr-010.txt
```

---

## Command: `contextgit link`

### Synopsis

```bash
contextgit link <FROM_ID> <TO_ID> --type <RELATION_TYPE>
```

### Description

Manually create or update a link between two nodes.

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `FROM_ID` | Yes | Source node ID |
| `TO_ID` | Yes | Target node ID |
| `RELATION_TYPE` | Yes (via `--type`) | Type of relationship |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--type` / `-t` | string | - | Relation type: `refines`, `implements`, `tests`, `derived_from`, `depends_on` |

### Behavior

1. Load index
2. Validate both node IDs exist
3. Check if link already exists:
   - If exists: update relation type
   - If not: create new link
4. Set `sync_status: ok` and `last_checked` to current time
5. Save index
6. Output confirmation

### Output

```
Created link: SR-010 → AR-020 (refines)
```

Or if updating:

```
Updated link: SR-010 → AR-020 (relation changed to: implements)
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 2 | Missing `--type` option | `Error: --type is required` |
| 3 | FROM_ID not found | `Error: Node not found: {FROM_ID}` |
| 3 | TO_ID not found | `Error: Node not found: {TO_ID}` |
| 4 | Invalid relation type | `Error: Invalid relation type: {TYPE}` |

### Examples

**Create link:**
```bash
$ contextgit link SR-010 AR-020 --type refines
Created link: SR-010 → AR-020 (refines)
```

**Update existing link:**
```bash
$ contextgit link SR-010 AR-020 --type implements
Updated link: SR-010 → AR-020 (relation changed to: implements)
```

---

## Command: `contextgit confirm`

### Synopsis

```bash
contextgit confirm <ID>
```

### Description

Mark a node as synchronized with its upstream dependencies. Sets `sync_status: ok` for all incoming links (where this node is downstream).

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `ID` | Yes | Node ID to confirm |

### Behavior

1. Load index
2. Find node by ID
3. Find all links where `to == ID` (incoming links)
4. For each link:
   - Set `sync_status: ok`
   - Update `last_checked` to current time
5. Update node's checksum to current file content checksum
6. Save index
7. Output confirmation

### Output

```
Confirmed sync for SR-010
Updated 2 upstream links:
  BR-001 → SR-010 (ok)
  BR-002 → SR-010 (ok)
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 3 | Node ID not found | `Error: Node not found: {ID}` |
| 3 | Source file not found | `Error: File not found: {FILE}` |

### Examples

**Confirm single node:**
```bash
$ contextgit confirm SR-010
Confirmed sync for SR-010
Updated 2 upstream links.
```

**After updating downstream requirements:**
```bash
# User modifies BR-001
$ contextgit scan docs/
...
Marked 2 downstream links as upstream_changed

# User reviews and updates SR-010 and SR-011
# User confirms sync
$ contextgit confirm SR-010
Confirmed sync for SR-010
Updated 1 upstream link: BR-001 → SR-010 (ok)

$ contextgit confirm SR-011
Confirmed sync for SR-011
Updated 1 upstream link: BR-001 → SR-011 (ok)
```

---

## Command: `contextgit next-id`

### Synopsis

```bash
contextgit next-id <TYPE> [OPTIONS]
```

### Description

Generate the next available ID for a given node type. Used by LLMs and developers to create new requirements.

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `TYPE` | Yes | Node type: `business`, `system`, `architecture`, `code`, `test`, `decision` |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` / `-f` | string | text | Output format: `text` or `json` |

### Behavior

1. Load config
2. Get prefix for TYPE from config (e.g., "SR-" for "system")
3. Load index
4. Find all node IDs with this prefix
5. Extract numeric portions and find max
6. Increment and format with zero-padding
7. Output new ID

### Output (Text Format)

```
SR-012
```

### Output (JSON Format)

```json
{
  "type": "system",
  "id": "SR-012"
}
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 4 | Invalid type | `Error: Invalid node type: {TYPE}` |
| 5 | Config not found | `Error: Could not load config` |

### Examples

**Generate next system requirement ID:**
```bash
$ contextgit next-id system
SR-012
```

**JSON output:**
```bash
$ contextgit next-id system --format json
{"type": "system", "id": "SR-012"}
```

**Use in LLM workflow:**
```bash
$ NEW_ID=$(contextgit next-id system)
$ echo "Creating requirement: $NEW_ID"
Creating requirement: SR-012
```

---

## Command: `contextgit relevant-for-file`

### Synopsis

```bash
contextgit relevant-for-file <PATH> [OPTIONS]
```

### Description

Find all nodes relevant to a specific source file. Useful for LLMs to discover related requirements when working on code.

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `PATH` | Yes | File path (relative to repo root) |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--depth` / `-d` | integer | 3 | How many link levels to traverse upstream |
| `--format` / `-f` | string | text | Output format: `text` or `json` |

### Behavior

1. Load index
2. Find nodes where `file == PATH`
3. For each found node, traverse upstream links up to `depth` levels
4. Collect all unique nodes encountered
5. Output results, sorted by distance (closest first)

### Output (Text Format)

```
Requirements relevant to src/logging/api.py:

Direct:
  C-120: "LoggingAPIHandler class" (code)

Upstream (1 level):
  AR-020: "REST API design for logging" (architecture)

Upstream (2 levels):
  SR-010: "System shall expose job execution logs via API" (system)

Upstream (3 levels):
  BR-001: "Scheduled jobs must be observable" (business)
```

### Output (JSON Format)

```json
{
  "file": "src/logging/api.py",
  "nodes": [
    {
      "id": "C-120",
      "type": "code",
      "title": "LoggingAPIHandler class",
      "file": "docs/03_architecture/api_design.md",
      "distance": 0
    },
    {
      "id": "AR-020",
      "type": "architecture",
      "title": "REST API design for logging",
      "file": "docs/03_architecture/api_design.md",
      "distance": 1
    },
    {
      "id": "SR-010",
      "type": "system",
      "title": "System shall expose job execution logs via API",
      "file": "docs/02_system/logging_api.md",
      "distance": 2
    },
    {
      "id": "BR-001",
      "type": "business",
      "title": "Scheduled jobs must be observable",
      "file": "docs/01_business/observability.md",
      "distance": 3
    }
  ]
}
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 3 | No nodes found for file | `Info: No requirements found for {PATH}` (exit 0, not an error) |
| 5 | Index not found | `Error: Could not load index` |

### Examples

**Find relevant requirements:**
```bash
$ contextgit relevant-for-file src/logging/api.py
Requirements relevant to src/logging/api.py:
  C-120: "LoggingAPIHandler class" (code)
  AR-020: "REST API design for logging" (architecture)
  SR-010: "System shall expose job execution logs via API" (system)
  BR-001: "Scheduled jobs must be observable" (business)
```

**Limit depth:**
```bash
$ contextgit relevant-for-file src/logging/api.py --depth 1
Requirements relevant to src/logging/api.py:
  C-120: "LoggingAPIHandler class" (code)
  AR-020: "REST API design for logging" (architecture)
```

**JSON output:**
```bash
$ contextgit relevant-for-file src/logging/api.py --format json
{"file": "src/logging/api.py", "nodes": [...]}
```

---

## Command: `contextgit fmt`

### Synopsis

```bash
contextgit fmt
```

### Description

Normalize and format the index file for clean git diffs. Sorts nodes by ID, sorts links by (from, to), and applies deterministic YAML formatting.

### Behavior

1. Load index
2. Sort nodes alphabetically by ID
3. Sort links alphabetically by (from, to) tuple
4. Apply deterministic YAML formatting:
   - 2-space indentation
   - Consistent key ordering
   - Block style for readability
5. Save index atomically
6. Output confirmation

### Output

```
Formatted .contextgit/requirements_index.yaml
Sorted 23 nodes, 48 links
```

### Error Conditions

| Exit Code | Condition | Message |
|-----------|-----------|---------|
| 5 | Index not found or corrupted | `Error: Could not load index` |

### Examples

**Format index:**
```bash
$ contextgit fmt
Formatted .contextgit/requirements_index.yaml
Sorted 23 nodes, 48 links
```

**Use before committing:**
```bash
$ contextgit scan docs/ --recursive
$ contextgit fmt
$ git add .contextgit
$ git commit -m "Update requirements"
```

---

## Exit Code Summary

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (e.g., .contextgit/ already exists) |
| 2 | Invalid arguments or options |
| 3 | File or node not found |
| 4 | Invalid metadata or data |
| 5 | Index or config file corrupted or not found |

---

## Common Patterns

### LLM Workflow: Create New Requirement

```bash
# Generate ID
NEW_ID=$(contextgit next-id system)

# LLM creates file with metadata containing $NEW_ID
# ...

# Scan to update index
contextgit scan docs/02_system --recursive

# Verify
contextgit show $NEW_ID
```

### LLM Workflow: Implement Requirement

```bash
# Extract requirement details
contextgit extract SR-010 --format json > /tmp/sr-010.json

# LLM reads context and implements code
# ...

# Update traceability (if code has metadata)
contextgit scan src/

# Check status
contextgit status --stale
```

### CI Workflow: Check Staleness

```bash
#!/bin/bash
# In CI pipeline

contextgit scan --recursive
STATUS=$(contextgit status --format json)
STALE=$(echo $STATUS | jq '.links.stale')

if [ "$STALE" -gt 0 ]; then
  echo "Error: $STALE stale links detected"
  contextgit status --stale
  exit 1
fi

echo "Requirements traceability check passed"
exit 0
```

---

## Summary

The contextgit CLI is designed to be:

- **Intuitive**: Clear command names and consistent flag patterns
- **Composable**: Commands can be piped and scripted
- **LLM-friendly**: JSON output for all read operations
- **Fast**: Most commands complete in under 500ms
- **Git-friendly**: Deterministic output for clean diffs

All commands follow Unix conventions and provide clear error messages to guide users toward resolution.
