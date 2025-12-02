# contextgit

**Requirements traceability for LLM-assisted software development**

contextgit is a local-first, git-friendly CLI tool that maintains bidirectional traceability between business requirements, system specifications, architecture decisions, source code, and tests. Designed specifically for integration with Claude Code and similar LLM development assistants.

## Features

- **Traceability Graph**: Track relationships from business needs → system specs → architecture → code → tests
- **Staleness Detection**: Automatically detect when upstream requirements change
- **LLM-Optimized**: JSON output for all commands; precise context extraction with `extract`
- **Git-Friendly**: Stores metadata in Markdown YAML frontmatter and HTML comments
- **Local-First**: All data stored in `.contextgit/requirements_index.yaml` - no network calls
- **Zero Runtime Dependencies**: Works offline, integrates seamlessly with git workflows

## Installation

```bash
# Install from source (development mode)
pip install -e .

# Or install from PyPI (when published)
pip install contextgit
```

## Quick Start

```bash
# 1. Initialize a contextgit repository
contextgit init

# 2. Add metadata to your Markdown files
cat > docs/requirements.md << 'EOF'
---
contextgit:
  id: BR-001
  type: business
  title: "User authentication"
  upstream: []
  downstream: []
---

# User Authentication

Users must be able to log in with email and password.
EOF

# 3. Scan files to build the index
contextgit scan docs/ --recursive

# 4. Check repository status
contextgit status

# 5. View requirement details
contextgit show BR-001

# 6. Extract requirement text for LLM
contextgit extract BR-001

# 7. Create implementation with linked requirements
cat > docs/system_requirements.md << 'EOF'
<!-- contextgit:
id: SR-001
type: system
title: "Authentication API endpoint"
upstream: [BR-001]
downstream: []
-->

## Authentication API

POST /api/auth/login endpoint accepting email and password.
EOF

# 8. Rescan to build traceability links
contextgit scan docs/ --recursive

# 9. Generate next ID for a new requirement
contextgit next-id system
# Output: SR-002
```

## Core Commands

### Initialization and Scanning

```bash
# Initialize repository
contextgit init

# Scan for metadata (current directory)
contextgit scan

# Scan recursively
contextgit scan docs/ --recursive

# Preview changes without saving
contextgit scan --dry-run
```

### Querying and Inspection

```bash
# Show project status
contextgit status

# Show only stale links
contextgit status --stale

# Show orphan nodes (no upstream/downstream)
contextgit status --orphans

# Show node details with links
contextgit show SR-010

# Extract requirement text for LLM
contextgit extract SR-010

# Find requirements relevant to source file
contextgit relevant-for-file src/auth/login.py
```

### Linking and Synchronization

```bash
# Create manual link between nodes
contextgit link BR-001 SR-010 --type refines

# Mark node as synchronized after reviewing upstream changes
contextgit confirm SR-010
```

### Utilities

```bash
# Generate next ID for node type
contextgit next-id business  # BR-001
contextgit next-id system    # SR-012

# Format index for clean git diffs
contextgit fmt

# Get JSON output (all commands support --format json)
contextgit show SR-010 --format json
```

## Metadata Format

contextgit supports two metadata formats in Markdown files:

### YAML Frontmatter (recommended)

```markdown
---
contextgit:
  id: SR-010
  type: system
  title: "User authentication system"
  upstream: [BR-001]
  downstream: [AR-005, CD-020]
  tags: [security, auth]
---

# System Requirement: User Authentication

Content here...
```

### HTML Comments (inline)

```markdown
<!-- contextgit:
id: SR-010
type: system
title: "User authentication system"
upstream: [BR-001]
downstream: [AR-005]
-->

## User Authentication

Content here...
```

## Node Types

- `business` - Business requirements (BR-*)
- `system` - System requirements (SR-*)
- `architecture` - Architecture decisions (AR-*)
- `code` - Code implementation notes (CD-*)
- `test` - Test specifications (TS-*)
- `decision` - Design decisions (DR-*)

## Relation Types

- `refines` - SR refines BR (system requirement refines business requirement)
- `implements` - Code implements SR/AR
- `tests` - Test tests code/requirement
- `depends_on` - General dependency
- `derived_from` - Derived from another node

## Sync Status

- `ok` - Node and upstream are synchronized
- `upstream_changed` - Upstream requirement has changed (checksum mismatch)
- `downstream_changed` - Downstream implementation has changed
- `broken` - Link target no longer exists

## LLM Integration

contextgit is designed for use with Claude Code and similar LLM development assistants:

```bash
# Get precise context for implementing a requirement
contextgit extract SR-010 > /tmp/requirement.txt

# Find all requirements affecting a file
contextgit relevant-for-file src/auth.py --format json

# Check for stale requirements before making changes
contextgit status --stale

# After updating code, rescan and confirm synchronization
contextgit scan src/ --recursive
contextgit confirm SR-010
```

All commands support `--format json` for easy parsing by LLMs.

## File Structure

```
.contextgit/
├── config.yaml              # Configuration (ID prefixes, directories)
└── requirements_index.yaml  # Central index (nodes, links, sync status)
```

## Performance Targets

- `extract`: < 100ms
- `show` / `status`: < 500ms
- `scan` 1000 files: < 5 seconds

## Documentation

For complete documentation, see the `docs/` directory:

- **Product Overview**: `docs/01_product_overview.md`
- **User Stories**: `docs/02_user_stories.md`
- **System Requirements**: `docs/03_system_requirements.md`
- **Architecture**: `docs/04_architecture_overview.md`
- **Data Model**: `docs/05_data_model_and_file_layout.md`
- **CLI Specification**: `docs/06_cli_specification.md`
- **LLM Integration**: `docs/07_llm_integration_guidelines.md`
- **MVP Scope**: `docs/08_mvp_scope_and_future_work.md`

## Requirements

- Python 3.11+
- Dependencies: `typer`, `rich`, `ruamel.yaml`, `markdown-it-py`

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run import validation
python3 test_imports.py

# Check CLI help
python3 -m contextgit --help
```

## Contributing

This is currently an MVP implementation. See `docs/08_mvp_scope_and_future_work.md` for planned features.

## License

[To be determined]

## Links

- Documentation: `docs/`
- Issue Tracker: [GitHub Issues]
- PyPI: [To be published]
