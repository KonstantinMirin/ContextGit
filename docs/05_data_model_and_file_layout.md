# Data Model and File Layout

## Overview

This document provides detailed schemas for all contextgit data structures, configuration files, and recommended repository layouts. All examples use YAML unless otherwise specified.

---

## Node Data Model

A **Node** represents a single requirement, design decision, or code artifact tracked by contextgit.

### Node Schema

```yaml
id: string                  # Unique identifier (e.g., "SR-010")
type: enum                  # Node type (see below)
title: string               # Short human-readable title (1-100 chars)
file: string                # Relative path from repo root (e.g., "docs/system/logging.md")
location: Location          # Where in the file this node lives (see below)
status: enum                # Current status (see below)
last_updated: string        # ISO 8601 timestamp (e.g., "2025-12-02T18:00:00Z")
checksum: string            # SHA-256 hash of the node's content (hex string)
llm_generated: boolean      # Optional, default false
tags: list[string]          # Optional, default []
```

### Node Type Enum

Supported values for the `type` field:

- `business`: Business requirement (high-level user need or goal)
- `system`: System requirement (technical capability the system must provide)
- `architecture`: Architecture decision or design specification
- `code`: Code-level artifact (function, class, module)
- `test`: Test specification or test case
- `decision`: Architecture Decision Record (ADR)
- `other`: Catch-all for other context items

### Node Status Enum

Supported values for the `status` field:

- `draft`: Work in progress, not yet finalized
- `active`: Current and authoritative
- `deprecated`: Superseded but kept for reference
- `superseded`: Replaced by another node (should reference replacement)

If omitted in metadata, defaults to `active`.

### Location Types

#### Heading-Based Location

For nodes identified by their position under a Markdown heading:

```yaml
kind: heading
path:
  - "Section Title"
  - "Subsection Title"
  - "Sub-subsection Title"
```

Example:
```yaml
location:
  kind: heading
  path:
    - "System Design – Logging"
    - "3.1 Logging API"
```

This means the node is located under the section with this heading path. When extracting, the tool reads from this heading through all content until the next heading of equal or higher level.

#### Line-Based Location

For nodes identified by explicit line ranges:

```yaml
kind: lines
start: integer    # Starting line number (1-indexed, inclusive)
end: integer      # Ending line number (1-indexed, inclusive)
```

Example:
```yaml
location:
  kind: lines
  start: 45
  end: 68
```

This means the node spans lines 45-68 in the file.

### Node Examples

#### Business Requirement Node

```yaml
id: BR-001
type: business
title: "Scheduled jobs must be observable"
file: docs/01_business/observability.md
location:
  kind: heading
  path:
    - "Business Requirements"
    - "Observability"
status: active
last_updated: "2025-12-02T17:00:00Z"
checksum: "a1b2c3d4e5f6..."
llm_generated: true
tags:
  - "feature:observability"
  - "priority:high"
```

#### System Requirement Node

```yaml
id: SR-010
type: system
title: "System shall expose job execution logs via API"
file: docs/02_system/logging_api.md
location:
  kind: heading
  path:
    - "System Design – Logging"
    - "3.1 Logging API"
status: active
last_updated: "2025-12-02T18:00:00Z"
checksum: "def456789abc..."
llm_generated: false
tags:
  - "feature:observability"
  - "api:rest"
```

#### Code Item Node

```yaml
id: C-120
type: code
title: "LoggingAPIHandler class"
file: docs/03_architecture/api_design.md
location:
  kind: heading
  path:
    - "API Design"
    - "Logging Endpoint Handler"
status: active
last_updated: "2025-12-02T19:00:00Z"
checksum: "123abc456def..."
llm_generated: false
tags:
  - "component:api"
  - "module:logging"
```

---

## Link Data Model

A **Link** represents a traceability relationship between two nodes.

### Link Schema

```yaml
from: string                # Source node ID (e.g., "BR-001")
to: string                  # Target node ID (e.g., "SR-010")
relation_type: enum         # Type of relationship (see below)
sync_status: enum           # Synchronization status (see below)
last_checked: string        # ISO 8601 timestamp
```

### Relation Type Enum

Supported values for the `relation_type` field:

- `refines`: The `to` node refines or elaborates on the `from` node
  - Example: BR-001 refines→ SR-010 (system requirement refines business requirement)
- `implements`: The `to` node implements the `from` node
  - Example: SR-010 implements→ C-120 (code implements system requirement)
- `tests`: The `to` node tests the `from` node
  - Example: C-120 tests→ T-050 (test validates code)
- `derived_from`: The `to` node is derived from the `from` node
  - Example: SR-010 derived_from→ BR-001 (alternative to refines)
- `depends_on`: The `to` node depends on the `from` node
  - Example: SR-011 depends_on→ SR-010 (dependency relationship)

### Sync Status Enum

Supported values for the `sync_status` field:

- `ok`: Both nodes are synchronized; checksums match last confirmed state
- `upstream_changed`: The `from` node has changed; `to` node may need update
- `downstream_changed`: The `to` node has changed; may indicate implementation divergence
- `broken`: One or both nodes no longer exist (file deleted, ID not found)

### Link Examples

#### Refinement Link (Business → System)

```yaml
from: BR-001
to: SR-010
relation_type: refines
sync_status: ok
last_checked: "2025-12-02T18:05:00Z"
```

This indicates SR-010 refines BR-001, and they're currently in sync.

#### Implementation Link (System → Code)

```yaml
from: SR-010
to: C-120
relation_type: implements
sync_status: upstream_changed
last_checked: "2025-12-02T19:00:00Z"
```

This indicates C-120 implements SR-010, but SR-010 has changed since the last sync. C-120 may need to be reviewed and updated.

#### Test Link (Code → Test)

```yaml
from: C-120
to: T-050
relation_type: tests
sync_status: ok
last_checked: "2025-12-02T19:30:00Z"
```

This indicates T-050 tests C-120, and they're in sync.

---

## Index File Structure

The central index file (`.contextgit/requirements_index.yaml`) stores all nodes and links.

### Index Schema

```yaml
nodes:
  - <Node 1>
  - <Node 2>
  - ...

links:
  - <Link 1>
  - <Link 2>
  - ...
```

### Full Index Example

```yaml
nodes:
  - id: BR-001
    type: business
    title: "Scheduled jobs must be observable"
    file: docs/01_business/observability.md
    location:
      kind: heading
      path:
        - "Business Requirements"
        - "Observability"
    status: active
    last_updated: "2025-12-02T17:00:00Z"
    checksum: "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
    llm_generated: true
    tags:
      - "feature:observability"

  - id: SR-010
    type: system
    title: "System shall expose job execution logs via API"
    file: docs/02_system/logging_api.md
    location:
      kind: heading
      path:
        - "System Design – Logging"
        - "3.1 Logging API"
    status: active
    last_updated: "2025-12-02T18:00:00Z"
    checksum: "def456789abc012345678901234567890abcdef1234567890abcdef123456789"
    llm_generated: false
    tags:
      - "feature:observability"
      - "api:rest"

  - id: AR-020
    type: architecture
    title: "REST API design for logging"
    file: docs/03_architecture/api_design.md
    location:
      kind: heading
      path:
        - "API Design"
        - "Logging Endpoints"
    status: active
    last_updated: "2025-12-02T18:30:00Z"
    checksum: "123abc456def789012345678901234567890abcdef1234567890abcdef123456"
    llm_generated: false
    tags:
      - "component:api"

links:
  - from: BR-001
    to: SR-010
    relation_type: refines
    sync_status: ok
    last_checked: "2025-12-02T18:05:00Z"

  - from: SR-010
    to: AR-020
    relation_type: refines
    sync_status: ok
    last_checked: "2025-12-02T18:35:00Z"
```

### Deterministic Ordering

For git-friendliness, the tool must maintain deterministic ordering:

- **Nodes**: Sorted alphabetically by `id`
- **Links**: Sorted alphabetically by `(from, to)` tuple
- **Keys within objects**: Alphabetical order (or fixed canonical order)
- **Lists within objects**: Maintain insertion order or sort alphabetically (e.g., tags)

---

## Config File Structure

The configuration file (`.contextgit/config.yaml`) defines project-specific settings.

### Config Schema

```yaml
tag_prefixes:
  business: string        # Prefix for business requirement IDs (e.g., "BR-")
  system: string          # Prefix for system requirement IDs (e.g., "SR-")
  architecture: string    # Prefix for architecture IDs (e.g., "AR-")
  code: string            # Prefix for code item IDs (e.g., "C-")
  test: string            # Prefix for test item IDs (e.g., "T-")
  decision: string        # Prefix for decision IDs (e.g., "ADR-")

directories:              # Optional: suggested directories for each type
  business: string
  system: string
  architecture: string
  code: string
  test: string
```

### Default Config Example

```yaml
tag_prefixes:
  business: "BR-"
  system: "SR-"
  architecture: "AR-"
  code: "C-"
  test: "T-"
  decision: "ADR-"

directories:
  business: "docs/01_business"
  system: "docs/02_system"
  architecture: "docs/03_architecture"
  code: "src"
  test: "tests"
```

The `directories` section is for documentation purposes only; contextgit does not enforce this structure. It can be used by LLMs to suggest where to create new files.

---

## Metadata Block Formats

Metadata blocks in Markdown files provide the source data for nodes.

### Format 1: YAML Frontmatter

Placed at the very beginning of a Markdown file:

```markdown
---
contextgit:
  id: SR-010
  type: system
  title: "System shall expose job execution logs via API"
  upstream: [BR-001]
  downstream: [AR-020, C-120]
  status: active
  tags:
    - "feature:observability"
    - "api:rest"
---

# System Design – Logging

The system shall provide a REST API endpoint `/api/logs` that returns...
```

- The `contextgit` key at the top level contains all metadata.
- `upstream` and `downstream` are lists of node IDs that define links.
- If `id: auto`, the tool will assign the next available ID during scanning.

### Format 2: Inline HTML Comment Block

Placed immediately before a section (heading):

```markdown
## 3.1 Logging API

<!-- contextgit
id: SR-010
type: system
title: "System shall expose job execution logs via API"
upstream: [BR-001]
downstream: [AR-020, C-120]
status: active
tags:
  - "feature:observability"
  - "api:rest"
-->

The system shall provide a REST API endpoint `/api/logs` that returns...
```

- The metadata is embedded in an HTML comment with YAML content.
- The comment should appear immediately before or after the relevant heading.
- Multiple comment blocks can exist in a single file (one per requirement).

### Link Creation from Metadata

When the tool scans a file and finds a node with:

```yaml
upstream: [BR-001, BR-002]
downstream: [AR-020]
```

It creates the following links:

- `BR-001 → SR-010` (relation type inferred based on node types, typically `refines`)
- `BR-002 → SR-010`
- `SR-010 → AR-020`

The relation type is inferred based on typical node type relationships:

| From Type    | To Type       | Inferred Relation |
|--------------|---------------|-------------------|
| business     | system        | refines           |
| business     | architecture  | refines           |
| system       | architecture  | refines           |
| architecture | code          | implements        |
| system       | code          | implements        |
| code         | test          | tests             |

If the relationship is non-standard, use `contextgit link` command to manually set the correct relation type.

---

## Repository Directory Layout

### Recommended Structure

```
my-project/
├── .git/                          # Git repository
├── .contextgit/                      # contextgit state directory
│   ├── config.yaml                # Project configuration
│   └── requirements_index.yaml    # Central index
│
├── docs/                          # Documentation directory
│   ├── 01_business/               # Business requirements
│   │   ├── overview.md
│   │   └── observability.md
│   │
│   ├── 02_system/                 # System requirements
│   │   ├── logging_api.md
│   │   └── job_execution.md
│   │
│   ├── 03_architecture/           # Architecture docs
│   │   ├── api_design.md
│   │   └── data_model.md
│   │
│   └── 04_decisions/              # Architecture Decision Records
│       ├── ADR-001-use-rest-api.md
│       └── ADR-002-logging-strategy.md
│
├── src/                           # Source code
│   ├── logging/
│   │   ├── __init__.py
│   │   └── api.py
│   └── ...
│
├── tests/                         # Tests
│   ├── test_logging.py
│   └── ...
│
├── README.md
└── pyproject.toml
```

This is a recommended structure, not enforced. contextgit works with any directory layout.

---

## Example: Complete Metadata Block in Context

### File: `docs/02_system/logging_api.md`

```markdown
# System Design – Logging

This document describes the logging subsystem for the job scheduler.

## Overview

The system must provide comprehensive logging for all job executions, including start time, end time, status, and output.

## 3.1 Logging API

<!-- contextgit
id: SR-010
type: system
title: "System shall expose job execution logs via API"
upstream: [BR-001]
downstream: [AR-020, C-120]
status: active
tags:
  - "feature:observability"
  - "api:rest"
-->

The system shall provide a REST API endpoint `/api/logs` that returns job execution logs. The API must support:

- Filtering by job ID
- Filtering by date range
- Filtering by status (success, failure, running)
- Pagination for large result sets

### API Specification

**Endpoint**: `GET /api/logs`

**Query Parameters**:
- `job_id` (optional): Filter by job ID
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `status` (optional): One of [success, failure, running]
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 50, max: 500)

**Response**:
```json
{
  "logs": [
    {
      "id": "log-12345",
      "job_id": "job-abc",
      "start_time": "2025-12-02T10:00:00Z",
      "end_time": "2025-12-02T10:05:00Z",
      "status": "success",
      "output": "Job completed successfully"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_count": 123
  }
}
```

## 3.2 Log Storage

...
```

When scanned, this produces a node:

```yaml
id: SR-010
type: system
title: "System shall expose job execution logs via API"
file: docs/02_system/logging_api.md
location:
  kind: heading
  path:
    - "System Design – Logging"
    - "3.1 Logging API"
status: active
last_updated: "2025-12-02T18:00:00Z"
checksum: "def456..."  # Hash of the section content
tags:
  - "feature:observability"
  - "api:rest"
```

And links:

```yaml
- from: BR-001
  to: SR-010
  relation_type: refines
  sync_status: ok
  last_checked: "2025-12-02T18:05:00Z"

- from: SR-010
  to: AR-020
  relation_type: refines
  sync_status: ok
  last_checked: "2025-12-02T18:05:00Z"

- from: SR-010
  to: C-120
  relation_type: implements
  sync_status: ok
  last_checked: "2025-12-02T18:05:00Z"
```

---

## Checksum Calculation

The checksum is calculated from the text content of the node's section, normalized as follows:

1. **Extract text**: From the heading (or start line) to the next same-level heading (or end line)
2. **Normalize**:
   - Strip leading/trailing whitespace from each line
   - Convert all line endings to `\n`
   - Remove any metadata block itself (don't include the `<!-- contextgit ... -->` comment)
3. **Hash**: Compute SHA-256 hash of the normalized UTF-8 bytes
4. **Format**: Store as hex string (64 characters)

Example:
```python
import hashlib

def calculate_checksum(text: str) -> str:
    # Normalize
    lines = text.split('\n')
    normalized_lines = [line.strip() for line in lines]
    normalized_text = '\n'.join(normalized_lines).strip()

    # Hash
    hash_obj = hashlib.sha256(normalized_text.encode('utf-8'))
    return hash_obj.hexdigest()
```

---

## ID Format and Generation

### ID Format

IDs consist of:
- **Prefix**: Defined in config (e.g., "SR-")
- **Number**: Zero-padded to 3 digits (e.g., "010")

Examples:
- `BR-001`, `BR-002`, ..., `BR-999`
- `SR-001`, `SR-010`, `SR-123`
- `ADR-001`, `ADR-042`

### ID Generation Algorithm

When generating a new ID for type "system":

1. Load config to get prefix: `"SR-"`
2. Load index and extract all node IDs
3. Filter to IDs starting with `"SR-"`
4. Extract numeric portions: `["001", "010", "011"]`
5. Parse as integers: `[1, 10, 11]`
6. Find max: `11`
7. Increment: `12`
8. Format: `"SR-" + str(12).zfill(3)` = `"SR-012"`

### Handling `id: auto`

If a metadata block has `id: auto`:

```markdown
<!-- contextgit
id: auto
type: system
title: "New system requirement"
-->
```

The tool will:
1. Generate the next ID (e.g., `SR-012`)
2. **Optionally** update the file to replace `id: auto` with `id: SR-012` (future enhancement)
3. For MVP: The ID is assigned in the index, but the file is not modified

---

## JSON Output Schemas

All commands with `--format json` output structured JSON.

### Status Command JSON

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

### Show Command JSON

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
    "checksum": "def456...",
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

### Extract Command JSON

```json
{
  "id": "SR-010",
  "file": "docs/02_system/logging_api.md",
  "location": {
    "kind": "heading",
    "path": ["System Design – Logging", "3.1 Logging API"]
  },
  "snippet": "The system shall provide a REST API endpoint `/api/logs` that returns job execution logs. The API must support:\n\n- Filtering by job ID\n- Filtering by date range\n..."
}
```

### Next-ID Command JSON

```json
{
  "type": "system",
  "id": "SR-012"
}
```

### Relevant-For-File Command JSON

```json
{
  "file": "src/logging/api.py",
  "nodes": [
    {
      "id": "C-120",
      "type": "code",
      "title": "LoggingAPIHandler class",
      "file": "docs/03_architecture/api_design.md"
    },
    {
      "id": "AR-020",
      "type": "architecture",
      "title": "REST API design for logging",
      "file": "docs/03_architecture/api_design.md"
    },
    {
      "id": "SR-010",
      "type": "system",
      "title": "System shall expose job execution logs via API",
      "file": "docs/02_system/logging_api.md"
    }
  ]
}
```

---

## Summary

The contextgit data model is designed to be:

- **Simple**: Plain YAML and Markdown, no complex schemas
- **Git-friendly**: Deterministic ordering, human-readable diffs
- **Extensible**: Can add fields without breaking existing tools
- **LLM-friendly**: Structured JSON output for all queries
- **Traceable**: Clear relationships between requirements at all levels

This design supports the MVP requirements while providing a foundation for future enhancements.
