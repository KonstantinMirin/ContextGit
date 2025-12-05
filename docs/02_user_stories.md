---
contextgit:
  id: BR-002
  type: business
  title: User stories and personas for contextgit
  status: active
  upstream:
    - BR-001
  tags: [mvp, user-stories, personas]
---

# User Stories

## Developer Personas

### Persona 1: Alex - Solo Developer with Claude CLI

**Background**:
- Freelance developer building a SaaS product
- Uses Claude Code extensively for generating requirements, design docs, and code
- Works alone, but wants to maintain professional documentation practices
- Values git-based workflows and automation
- Struggles with keeping requirements and code in sync as the project evolves

**Goals**:
- Maintain clear traceability from business ideas to working code
- Quickly find which requirements relate to code they're working on
- Get alerted when upstream requirements change so downstream docs/code can be updated
- Help Claude Code provide accurate context when generating or modifying code

**Pain Points**:
- Currently has requirements scattered across multiple Markdown files
- No automated way to know when requirements change
- Wastes time manually tracking "what implements what"
- Claude Code sometimes uses outdated requirements because it can't tell what's current

### Persona 2: Jordan - Tech Lead on Small Team

**Background**:
- Leads a team of 3 developers building an internal tool
- Team uses Claude Code and other LLM tools to accelerate development
- Reviews code and ensures alignment with requirements
- Runs CI/CD pipelines that should catch stale documentation
- Wants the team to maintain good traceability without heavy process overhead

**Goals**:
- Ensure all code has traceable requirements
- Detect when PRs change code but don't update related requirements
- Help team members find relevant requirements when working on features
- Maintain documentation that's useful, not just "checkbox compliance"

**Pain Points**:
- Currently relies on manual code review to catch documentation drift
- No automated way to flag when requirements are orphaned or stale
- Team members sometimes duplicate requirements because they can't find existing ones
- Difficult to onboard new developers when requirements are scattered

## User Stories

### Story 1: Initialize Project for Requirements Tracking

**As** Alex (solo developer),
**I want to** initialize my project repository to use contextgit,
**So that** I can start tracking requirements and their relationships from the beginning.

**Acceptance Criteria**:
- Running `contextgit init` creates `.contextgit/config.yaml` with sensible defaults
- Running `contextgit init` creates an empty `.contextgit/requirements_index.yaml`
- Config file includes default tag prefixes (BR-, SR-, AR-, C-, T-, ADR-)
- Config file suggests default directory structure for organizing requirements
- Command completes in under 1 second
- Generated files are git-friendly (deterministic formatting)

**Flow**:
1. Alex creates a new project directory and initializes git
2. Alex runs `contextgit init`
3. Tool asks a few optional questions (or uses defaults):
   - "Where will business requirements live?" (default: `docs/01_business/`)
   - "Where will system requirements live?" (default: `docs/02_system/`)
   - etc.
4. Tool creates `.contextgit/` directory and initial files
5. Alex commits the initial setup: `git add .contextgit && git commit -m "Initialize contextgit"`

---

### Story 2: Create a Business Requirement with Metadata

**As** Alex,
**I want to** create a new business requirement document with embedded metadata,
**So that** contextgit can track it and Claude Code can reference it precisely.

**Acceptance Criteria**:
- Alex can create a Markdown file with a contextgit metadata block
- Metadata includes: `id`, `type`, `title`, `upstream`, `downstream`
- The `id` can be generated via `contextgit next-id business`
- The metadata block is either YAML frontmatter or an inline HTML comment
- Claude Code recognizes the project uses contextgit (by detecting `.contextgit/config.yaml`)

**Flow**:
1. Alex asks Claude Code: "Create a business requirement for job scheduling observability"
2. Claude Code detects `.contextgit/config.yaml` and knows to use contextgit conventions
3. Claude Code runs `contextgit next-id business` to get next ID: `BR-001`
4. Claude Code creates `docs/01_business/observability.md`:
   ```markdown
   ---
   contextgit:
     id: BR-001
     type: business
     title: "Scheduled jobs must be observable"
     upstream: []
     downstream: []
   ---
   # Business Requirement: Observability

   Users must be able to monitor the execution status of all scheduled jobs...
   ```
5. Alex reviews and commits the file

---

### Story 3: Scan Files and Build the Index

**As** Alex,
**I want to** scan my documentation files to build a central index,
**So that** contextgit knows about all requirements and can track them.

**Acceptance Criteria**:
- Running `contextgit scan docs/ --recursive` finds all contextgit metadata blocks
- Index is updated at `.contextgit/requirements_index.yaml`
- Each node includes: id, type, title, file, location, checksum, timestamps
- Links are created based on `upstream` and `downstream` fields
- Command reports what was added/updated (or supports `--format json`)
- Running scan multiple times is idempotent (only updates if content changed)

**Flow**:
1. Alex has created several requirement documents with metadata
2. Alex runs `contextgit scan docs/ --recursive`
3. Tool outputs:
   ```
   Scanned 3 files
   Added 5 nodes: BR-001, BR-002, SR-010, SR-011, AR-020
   Created 4 links
   Index updated: .contextgit/requirements_index.yaml
   ```
4. Alex reviews the index file and sees all nodes and links listed
5. Alex commits: `git add .contextgit docs && git commit -m "Add initial requirements"`

---

### Story 4: Create a System Requirement Linked to Business Requirement

**As** Alex,
**I want to** create a system requirement that refines a business requirement,
**So that** there's clear traceability from business needs to technical specs.

**Acceptance Criteria**:
- Alex (or Claude Code) creates a new system requirement doc
- The system requirement's metadata specifies `upstream: [BR-001]`
- After running `contextgit scan`, the index shows a link from BR-001 to SR-010
- The link has `relation_type: refines` and `sync_status: ok`

**Flow**:
1. Alex asks Claude Code: "Create a system requirement for exposing job logs via API, implementing BR-001"
2. Claude Code runs `contextgit next-id system` → gets `SR-010`
3. Claude Code creates `docs/02_system/logging_api.md`:
   ```markdown
   ---
   contextgit:
     id: SR-010
     type: system
     title: "System shall expose job execution logs via API"
     upstream: [BR-001]
     downstream: []
   ---
   # System Requirement: Logging API

   The system shall provide a REST API endpoint...
   ```
4. Alex runs `contextgit scan docs/`
5. Tool creates link: `BR-001 --[refines]--> SR-010`
6. Alex can now run `contextgit show BR-001` and see SR-010 listed as a downstream requirement

---

### Story 5: Extract a Requirement Snippet for LLM Context

**As** Alex,
**I want to** extract just the content of a specific requirement by its ID,
**So that** Claude Code can work with precise context instead of loading entire files.

**Acceptance Criteria**:
- Running `contextgit extract SR-010` outputs only the section of the file containing SR-010
- Output can be plain text or JSON (`--format json`)
- JSON output includes: `id`, `file`, `snippet`, `location`
- Command completes in under 100ms

**Flow**:
1. Alex is working on implementing SR-010
2. Alex asks Claude Code: "Show me the details of SR-010"
3. Claude Code runs `contextgit extract SR-010 --format json`
4. Tool returns:
   ```json
   {
     "id": "SR-010",
     "file": "docs/02_system/logging_api.md",
     "location": {"kind": "heading", "path": ["System Requirement: Logging API"]},
     "snippet": "The system shall provide a REST API endpoint..."
   }
   ```
5. Claude Code uses only this snippet for context, saving tokens
6. Alex gets accurate, focused assistance from Claude Code

---

### Story 6: Detect When Upstream Requirement Changes

**As** Alex,
**I want to** be notified when a business requirement changes,
**So that** I can update downstream system requirements and code.

**Acceptance Criteria**:
- When BR-001 is modified, its checksum changes
- Running `contextgit scan` detects the checksum change
- All links from BR-001 are marked with `sync_status: upstream_changed`
- Running `contextgit status --stale` shows which downstream items need review
- After reviewing and updating SR-010, running `contextgit confirm SR-010` marks the link as synced

**Flow**:
1. Alex modifies the content of `BR-001` to add a new constraint
2. Alex runs `contextgit scan docs/`
3. Tool outputs:
   ```
   Node BR-001 changed (checksum updated)
   Marked 2 downstream links as upstream_changed
   ```
4. Alex runs `contextgit status --stale`:
   ```
   Stale links (downstream needs update):
   - BR-001 → SR-010 (upstream_changed)
   - BR-001 → SR-011 (upstream_changed)
   ```
5. Alex reviews SR-010 and SR-011, updates them to reflect BR-001 changes
6. Alex runs `contextgit scan docs/` to update their checksums
7. Alex runs `contextgit confirm SR-010` and `contextgit confirm SR-011`
8. Links are now marked `sync_status: ok`

---

### Story 7: Find Requirements Relevant to a Source File

**As** Alex,
**I want to** find all requirements related to a specific source file,
**So that** Claude Code can use relevant context when modifying that file.

**Acceptance Criteria**:
- Running `contextgit relevant-for-file src/logging/api.py` returns IDs of related requirements
- The command considers:
  - Code-level nodes (C-120) that directly reference the file
  - Architecture and system requirements (AR-020, SR-010) linked upstream from those code nodes
- Output can be JSON for programmatic use
- Command completes in under 200ms

**Flow**:
1. Alex is working on `src/logging/api.py`
2. Alex asks Claude Code: "Refactor the logging API handler"
3. Claude Code runs `contextgit relevant-for-file src/logging/api.py --format json`
4. Tool returns:
   ```json
   {
     "file": "src/logging/api.py",
     "nodes": [
       {"id": "C-120", "type": "code", "title": "LoggingAPIHandler class"},
       {"id": "AR-020", "type": "architecture", "title": "REST API design for logging"},
       {"id": "SR-010", "type": "system", "title": "System shall expose job logs via API"}
     ]
   }
   ```
5. Claude Code loads these specific requirement snippets using `contextgit extract`
6. Claude Code provides a refactoring that aligns with the requirements

---

### Story 8: Check Overall Project Health

**As** Jordan (tech lead),
**I want to** see a summary of the requirements traceability status,
**So that** I can identify gaps and stale documentation at a glance.

**Acceptance Criteria**:
- Running `contextgit status` shows:
  - Total nodes by type (business, system, architecture, code, test)
  - Total links
  - Count of stale links (upstream_changed, downstream_changed, broken)
  - Count of orphan nodes (no upstream or no downstream)
- Can filter by `--type`, `--file`, `--orphans`, `--stale`
- Supports `--format json` for CI integration

**Flow**:
1. Jordan runs `contextgit status` in the project root
2. Tool outputs:
   ```
   contextgit status:

   Nodes:
     business: 5
     system: 12
     architecture: 8
     code: 23
     test: 15

   Links: 48

   Health:
     Stale links: 3
     Broken links: 0
     Orphan nodes: 2 (no downstream)

   Run 'contextgit status --stale' for details.
   ```
3. Jordan runs `contextgit status --orphans`:
   ```
   Orphan nodes (no downstream):
   - SR-015: "System shall support async job processing"
   - AR-025: "Cache layer architecture"
   ```
4. Jordan assigns tasks to implement these requirements

---

### Story 9: Create Manual Link Between Requirements

**As** Jordan,
**I want to** manually create a link between two requirements,
**So that** I can express relationships that aren't captured in metadata blocks.

**Acceptance Criteria**:
- Running `contextgit link SR-010 AR-020 --type refines` creates a link
- The link appears in the index with `sync_status: ok` by default
- Running `contextgit show SR-010` displays the new downstream link to AR-020
- Changes are reflected in `.contextgit/requirements_index.yaml`

**Flow**:
1. Jordan realizes that SR-010 should link to AR-020, but the metadata doesn't reflect this
2. Jordan runs `contextgit link SR-010 AR-020 --type refines`
3. Tool outputs:
   ```
   Created link: SR-010 → AR-020 (refines)
   ```
4. Jordan runs `contextgit show SR-010` and sees AR-020 listed under downstream
5. Jordan commits: `git add .contextgit && git commit -m "Link SR-010 to AR-020"`

---

### Story 10: Use in CI to Block PRs with Stale Requirements

**As** Jordan,
**I want to** run contextgit in CI to detect stale requirements,
**So that** PRs can't be merged if they introduce or leave stale documentation.

**Acceptance Criteria**:
- Running `contextgit status --format json` returns structured data
- CI script can parse the JSON and fail if `stale_links > 0`
- CI provides clear error message listing which requirements are stale
- Developers can fix by updating docs and running `contextgit confirm`

**Flow**:
1. Jordan adds a CI step in `.github/workflows/ci.yml`:
   ```yaml
   - name: Check requirements traceability
     run: |
       pip install contextgit
       contextgit scan docs/ --recursive
       contextgit status --format json > status.json
       python scripts/check_contextgit.py status.json
   ```
2. A developer opens a PR that modifies a business requirement but doesn't update downstream system requirements
3. CI runs and detects `stale_links: 2`
4. CI fails with message:
   ```
   Requirements traceability check failed.
   Stale links detected:
   - BR-003 → SR-012 (upstream_changed)
   - BR-003 → SR-013 (upstream_changed)

   Please update downstream requirements and run 'contextgit confirm'.
   ```
5. Developer updates SR-012 and SR-013, runs `contextgit scan` and `contextgit confirm`
6. Developer pushes updated changes, CI passes

---

### Story 11: Format Index for Clean Git Diffs

**As** Alex,
**I want to** normalize the index file format,
**So that** git diffs are clean and reviewable even when multiple people update requirements.

**Acceptance Criteria**:
- Running `contextgit fmt` sorts nodes by ID alphabetically
- Running `contextgit fmt` sorts links by (from, to) pairs
- YAML formatting is deterministic (consistent indentation, key ordering)
- Command is idempotent (running twice produces identical output)

**Flow**:
1. After multiple scans and updates, the index file has nodes in random order
2. Alex runs `contextgit fmt`
3. Tool outputs:
   ```
   Formatted .contextgit/requirements_index.yaml
   Sorted 23 nodes, 48 links
   ```
4. Alex reviews `git diff` and sees that only the ordering changed, no data lost
5. Alex commits: `git add .contextgit && git commit -m "Format contextgit index"`

---

## Anti-Patterns and Edge Cases

### Anti-Pattern 1: Over-Engineering Requirements
**Problem**: Alex creates dozens of tiny, granular requirements for every detail.
**Solution**: Tool encourages meaningful grouping; documentation provides guidance on appropriate granularity (features, not functions).

### Anti-Pattern 2: Ignoring Staleness Warnings
**Problem**: Jordan's team sees stale warnings but ignores them because they're too noisy.
**Solution**: Tool should have clear thresholds; only mark as stale when checksums genuinely differ. Provide `contextgit confirm` as an easy way to acknowledge intentional non-updates.

### Edge Case 1: Circular Dependencies
**Problem**: BR-001 → SR-010 → AR-020 → BR-001
**Solution**: CLI should detect and warn about circular links during `contextgit scan`, but not block (might be intentional feedback loops).

### Edge Case 2: Merge Conflicts in Index
**Problem**: Two branches add different requirements with same ID.
**Solution**: Tool should detect ID conflicts during `contextgit scan` and report clear error. Users resolve by manually renumbering.

### Edge Case 3: File Moved or Deleted
**Problem**: A requirement file is moved or deleted, but index still references it.
**Solution**: `contextgit scan` detects missing files and marks links as `broken`. User can manually update file paths or remove nodes.

### Edge Case 4: Multiple Metadata Blocks in One File
**Problem**: A single Markdown file has 5 different system requirements as sections.
**Solution**: Tool should support multiple inline metadata blocks per file. Each gets its own node with unique location (heading path or line range).
