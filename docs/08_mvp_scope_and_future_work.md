# MVP Scope and Future Work

## Overview

This document clearly delineates what is **in scope** for the Minimum Viable Product (MVP) of contextgit and what is explicitly **out of scope** but may be considered for future versions. This ensures the MVP remains focused, achievable, and delivers core value quickly.

---

## MVP Definition

The MVP is defined as:

> **A local-first, git-friendly CLI tool that enables developers using LLM assistants (especially Claude Code) to track requirements and context traceability from business needs to code, detect staleness automatically, and extract precise context snippets for efficient LLM workflows.**

**Target Timeline:** The MVP should be achievable in 4-6 weeks of focused development by a single developer or small team.

**Success Criteria:**
1. A developer can initialize a project, create requirements with metadata, scan files, and view traceability
2. Claude Code can detect contextgit projects and use CLI commands to extract context
3. The tool detects when upstream requirements change and marks downstream items as stale
4. All operations work locally without network access
5. The tool produces git-friendly diffs
6. Documentation is complete and usable

---

## In Scope for MVP

### Core Functionality

#### 1. Project Initialization
- ✅ `contextgit init` command
- ✅ Create `.contextgit/config.yaml` with defaults
- ✅ Create empty `.contextgit/requirements_index.yaml`
- ✅ Support basic configuration (tag prefixes, directory suggestions)

#### 2. Metadata Format Support
- ✅ YAML frontmatter in Markdown files
- ✅ Inline HTML comment blocks with YAML content
- ✅ Support for node types: business, system, architecture, code, test, decision
- ✅ Support for required fields: id, type, title
- ✅ Support for optional fields: upstream, downstream, status, tags, llm_generated

#### 3. File Scanning
- ✅ `contextgit scan` command
- ✅ Scan single file or directory (with `--recursive`)
- ✅ Parse YAML frontmatter and inline comment blocks
- ✅ Extract location (heading path or line range)
- ✅ Calculate checksums for change detection
- ✅ Update index with nodes and links
- ✅ Support `--dry-run` and `--format json`

#### 4. Index Management
- ✅ Central index at `.contextgit/requirements_index.yaml`
- ✅ Store nodes with full metadata
- ✅ Store links with relation types and sync status
- ✅ Atomic file writes (write to temp, rename)
- ✅ Deterministic YAML formatting for git-friendliness

#### 5. Traceability Tracking
- ✅ Create links from `upstream` and `downstream` metadata fields
- ✅ Infer relation types based on node types
- ✅ Track sync status: ok, upstream_changed, downstream_changed, broken
- ✅ Detect checksum changes and update sync status

#### 6. Status and Health Reporting
- ✅ `contextgit status` command
- ✅ Show node counts by type
- ✅ Show link counts (total, stale, broken)
- ✅ Identify orphan nodes (no upstream or no downstream)
- ✅ Support filters: `--orphans`, `--stale`, `--file`, `--type`
- ✅ Support `--format json`

#### 7. Node Query
- ✅ `contextgit show <ID>` command
- ✅ Display node metadata
- ✅ Display upstream and downstream links
- ✅ Support `--format json`
- ✅ Support `--graph` for simple text-based graph view

#### 8. Context Extraction
- ✅ `contextgit extract <ID>` command
- ✅ Extract snippet by heading path or line range
- ✅ Output plain text or JSON
- ✅ Fast operation (< 100ms for typical files)

#### 9. Manual Link Management
- ✅ `contextgit link <FROM> <TO> --type <relation>` command
- ✅ Create or update links manually
- ✅ Support relation types: refines, implements, tests, derived_from, depends_on

#### 10. Synchronization Confirmation
- ✅ `contextgit confirm <ID>` command
- ✅ Mark incoming links as synced
- ✅ Update checksums to current state

#### 11. ID Generation
- ✅ `contextgit next-id <type>` command
- ✅ Generate sequential IDs with zero-padding
- ✅ Read prefixes from config
- ✅ Support `--format json`

#### 12. File-Based Relevance
- ✅ `contextgit relevant-for-file <path>` command
- ✅ Find nodes related to a specific file
- ✅ Traverse upstream links (configurable depth)
- ✅ Support `--format json`

#### 13. Index Formatting
- ✅ `contextgit fmt` command
- ✅ Sort nodes by ID
- ✅ Sort links by (from, to)
- ✅ Deterministic YAML formatting

### Non-Functional Requirements (MVP)

#### Platform Support
- ✅ Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)
- ✅ Python 3.11+
- ⚠️ macOS and Windows: "best effort" (not primary target, but should work)

#### Performance
- ✅ Handle up to 5,000 nodes and 10,000 links
- ✅ Scan up to 1,000 files in < 5 seconds
- ✅ Extract command completes in < 100ms
- ✅ Status and show commands complete in < 500ms

#### Reliability
- ✅ Atomic file writes (never corrupt index)
- ✅ Graceful error handling
- ✅ Clear error messages
- ✅ Validate index structure before writing

#### Usability
- ✅ Clear `--help` for all commands
- ✅ Human-readable error messages
- ✅ Consistent terminology
- ✅ Unix conventions (exit codes, stdout/stderr)

#### Git-Friendliness
- ✅ Plain-text YAML storage
- ✅ Deterministic ordering (sorted by ID)
- ✅ Human-readable diffs
- ✅ Relative file paths only

#### LLM Integration
- ✅ All read commands support `--format json`
- ✅ Fast command execution (< 200ms for common operations)
- ✅ Detectable via `.contextgit/config.yaml`
- ✅ Auto-detect repo root

### Documentation (MVP)

- ✅ README.md with installation and quick start
- ✅ Comprehensive planning documents (this set of 8 docs)
- ✅ Example project demonstrating usage
- ✅ Contributing guidelines (basic)
- ✅ LICENSE file (MIT or Apache 2.0)

### Packaging (MVP)

- ✅ Installable via `pip install contextgit`
- ✅ Command-line entry point: `contextgit`
- ✅ Minimal dependencies (prefer stdlib)
- ✅ Total installed size < 5 MB

---

## Explicitly Out of Scope for MVP

### Features Deferred to Future Versions

#### 1. Advanced File Format Support
- ❌ ReStructuredText (RST) parsing
- ❌ AsciiDoc parsing
- ❌ Parsing metadata from source code comments (Python docstrings, JSDoc, etc.)
- ❌ Support for non-Markdown files

**Rationale:** Markdown is sufficient for MVP; other formats add complexity without significant value initially.

**Future Version:** Phase 2

---

#### 2. Automatic ID Assignment in Files
- ❌ Replacing `id: auto` with actual IDs in files after scanning
- ❌ Writing back to source files

**Rationale:** File modification adds risk of corrupting user content. The index-based approach is safer for MVP.

**Future Version:** Phase 2 (optional enhancement)

---

#### 3. Code-Level Parsing
- ❌ Parsing Python source code to extract function/class definitions
- ❌ Auto-linking code artifacts to requirements based on docstrings
- ❌ Generating code-level nodes automatically

**Rationale:** Code parsing is complex and language-specific. Manual documentation of code artifacts is sufficient for MVP.

**Future Version:** Phase 3

---

#### 4. VS Code Extension
- ❌ Side panel showing node tree
- ❌ Inline badges for stale nodes
- ❌ Graph visualization (webview)
- ❌ Quick navigation to node files

**Rationale:** The CLI is the core; VS Code extension is a nice-to-have UI enhancement.

**Future Version:** Phase 2 (separate project)

---

#### 5. Watch Mode
- ❌ Continuous file watching with automatic scanning
- ❌ Real-time index updates

**Rationale:** Manual `scan` after changes is acceptable for MVP. Watch mode adds complexity.

**Future Version:** Phase 2

---

#### 6. Git Hooks
- ❌ Pre-commit hook to auto-scan
- ❌ Pre-push hook to check for stale links
- ❌ Automated hook installation

**Rationale:** Users can manually add hooks if desired; automated hook management is not essential for MVP.

**Future Version:** Phase 2 (documentation on how to set up hooks)

---

#### 7. CI/CD Integration Plugins
- ❌ GitHub Action
- ❌ GitLab CI template
- ❌ Jenkins plugin

**Rationale:** Users can call `contextgit` commands directly in CI scripts. Dedicated plugins are not essential.

**Future Version:** Phase 3

---

#### 8. Web-Based Dashboard
- ❌ SaaS platform
- ❌ Web UI for viewing traceability
- ❌ Interactive graph visualization
- ❌ Real-time collaboration

**Rationale:** Local-first CLI is the core value proposition. Web UI is a completely separate product.

**Future Version:** Phase 4 or separate product

---

#### 9. Issue Tracker Integration
- ❌ GitHub Issues sync
- ❌ JIRA integration
- ❌ Linear integration
- ❌ Bidirectional sync

**Rationale:** Integration with external systems adds complexity and reduces focus. Users can manually link if needed.

**Future Version:** Phase 4

---

#### 10. Advanced Graph Operations
- ❌ Shortest path queries
- ❌ Transitive closure (full impact analysis)
- ❌ Cycle detection and resolution suggestions
- ❌ Graph export (DOT, GraphML, etc.)

**Rationale:** Basic traceability is sufficient for MVP. Advanced graph queries are nice-to-have.

**Future Version:** Phase 3

---

#### 11. Requirements Templates
- ❌ Built-in templates for common requirement types
- ❌ Template generation commands
- ❌ Custom template support

**Rationale:** Users can copy-paste examples. Templates add UI complexity.

**Future Version:** Phase 2

---

#### 12. Multi-Repository Support
- ❌ Linking requirements across multiple repos
- ❌ Mono-repo support with multiple index files
- ❌ Cross-repo traceability

**Rationale:** Single-repo is the primary use case. Multi-repo adds significant complexity.

**Future Version:** Phase 4

---

#### 13. Collaboration Features
- ❌ User comments on nodes
- ❌ Approval workflows
- ❌ Assignment and ownership tracking
- ❌ Notifications

**Rationale:** Git-based collaboration (via commits and PRs) is sufficient for MVP.

**Future Version:** Phase 4 or separate product

---

#### 14. Advanced Reporting
- ❌ Coverage reports (% of code with traceability)
- ❌ Staleness trends over time
- ❌ HTML or PDF report generation
- ❌ Metrics dashboard

**Rationale:** Basic status command is sufficient. Advanced reporting is nice-to-have.

**Future Version:** Phase 3

---

#### 15. Import/Export
- ❌ Import from JIRA, Confluence, etc.
- ❌ Export to Excel, CSV, etc.
- ❌ Compatibility with other traceability tools

**Rationale:** The tool is self-contained. Import/export is not essential for MVP.

**Future Version:** Phase 3

---

#### 16. Access Control
- ❌ User authentication
- ❌ Role-based access control (RBAC)
- ❌ Permission management
- ❌ Audit logging

**Rationale:** Local-first tool assumes trusted environment. Access control is for enterprise features.

**Future Version:** Phase 5 (enterprise edition)

---

#### 17. Localization
- ❌ Multi-language support for UI
- ❌ Internationalization (i18n)

**Rationale:** English-only is sufficient for MVP. Most developers work in English.

**Future Version:** Phase 4

---

#### 18. Cloud Backup
- ❌ Automatic backup to cloud storage
- ❌ Sync across machines

**Rationale:** Git provides version control and sync. No need for separate backup.

**Future Version:** Not planned (use git)

---

## Roadmap: Future Phases

### Phase 2: Enhanced Tooling (3-4 months after MVP)

**Goal:** Improve developer experience with automation and IDE integration.

**Features:**
- VS Code extension with:
  - Side panel showing node tree
  - Quick navigation to nodes
  - Inline badges for stale nodes
- Watch mode for automatic scanning
- Support for ReStructuredText and AsciiDoc
- Pre-commit and pre-push hook templates (documentation)
- Requirement templates and scaffolding
- Improved error messages with suggestions
- Performance optimizations for large projects (10K+ nodes)

**Success Criteria:**
- VS Code extension has 1,000+ installs
- Watch mode is stable and performant
- Users report improved productivity

---

### Phase 3: Advanced Analytics and Integration (6-9 months after MVP)

**Goal:** Provide insights and integrate with development workflows.

**Features:**
- Advanced graph queries:
  - Shortest path between nodes
  - Impact analysis (full transitive closure)
  - Cycle detection and resolution
- Code-level parsing for Python:
  - Auto-extract functions and classes
  - Auto-link based on docstrings
- Coverage reporting:
  - % of requirements with tests
  - % of code with traceability
  - Staleness trends over time
- CI/CD integration:
  - GitHub Action
  - GitLab CI template
  - Pre-built Docker image
- HTML report generation

**Success Criteria:**
- Users integrate contextgit into CI pipelines
- Code-level parsing reduces manual documentation by 30%
- Coverage reports help teams improve traceability

---

### Phase 4: Collaboration and Ecosystem (12-18 months after MVP)

**Goal:** Support team collaboration and ecosystem growth.

**Features:**
- Multi-repository support (mono-repos and cross-repo linking)
- Issue tracker integration:
  - GitHub Issues
  - JIRA (read-only)
- Enhanced collaboration:
  - Comments on nodes (stored in separate YAML files)
  - Assignment and ownership
- Plugin system for extensibility
- Community-contributed templates and tools
- Localization (initial languages: English, Spanish, Chinese)

**Success Criteria:**
- 10,000+ active users
- 50+ community plugins
- Teams use contextgit for cross-repo projects

---

### Phase 5: Enterprise Features (18+ months after MVP)

**Goal:** Support large organizations with compliance and security requirements.

**Features:**
- SaaS platform (optional):
  - Web dashboard with interactive graph
  - Real-time collaboration
  - Centralized index for teams
- Access control and audit logging
- Compliance reporting (FDA, ISO, etc.)
- Advanced security features:
  - Encryption at rest
  - SSO integration
- Multi-language code parsing (Java, JavaScript, Go, etc.)
- Integration with enterprise tools (Azure DevOps, ServiceNow, etc.)

**Success Criteria:**
- 100+ enterprise customers
- Compliance certifications (SOC 2, ISO 27001)
- Annual recurring revenue (ARR) supports development team

---

## Decision Framework: What Belongs in MVP?

When evaluating whether a feature should be in the MVP, apply these criteria:

### ✅ Include in MVP if:
1. **Core to the value proposition**: Without it, the tool doesn't solve the main problem
2. **Blocking for LLM integration**: Claude Code and other LLMs can't use the tool effectively without it
3. **Required for git-friendliness**: Without it, the tool doesn't integrate well with git workflows
4. **Simple to implement**: Low complexity, high value
5. **No workaround exists**: Users can't achieve the same result another way

### ❌ Exclude from MVP if:
1. **Nice-to-have**: Improves UX but doesn't block core workflows
2. **Complex**: Requires significant development time or introduces risk
3. **Has a workaround**: Users can achieve the same result with a bit of manual work
4. **Niche use case**: Only a small subset of users would benefit
5. **Requires infrastructure**: Needs servers, databases, cloud services, etc.

### Example Decisions

| Feature | Decision | Rationale |
|---------|----------|-----------|
| `contextgit extract` | ✅ Include | Core to LLM integration; no workaround |
| Watch mode | ❌ Exclude | Users can run `scan` manually; adds complexity |
| VS Code extension | ❌ Exclude | Nice-to-have; CLI is sufficient for MVP |
| `contextgit confirm` | ✅ Include | Essential for staleness workflow; simple to implement |
| Code parsing | ❌ Exclude | Complex; manual documentation works for MVP |
| JSON output | ✅ Include | Blocking for LLM integration; simple to add |

---

## MVP Milestones

### Milestone 1: Core CLI (Weeks 1-2)
- ✅ Project structure and setup
- ✅ `contextgit init` command
- ✅ Config and index file management
- ✅ Basic CLI framework (Typer or Click)

### Milestone 2: Scanning and Indexing (Weeks 2-3)
- ✅ Metadata parsing (YAML frontmatter and inline comments)
- ✅ `contextgit scan` command
- ✅ Location resolution (heading paths and line ranges)
- ✅ Checksum calculation
- ✅ Link creation from metadata

### Milestone 3: Querying and Extraction (Week 3-4)
- ✅ `contextgit show` command
- ✅ `contextgit extract` command
- ✅ `contextgit status` command
- ✅ `contextgit relevant-for-file` command

### Milestone 4: Traceability Management (Week 4)
- ✅ Sync status tracking
- ✅ `contextgit link` command
- ✅ `contextgit confirm` command
- ✅ Staleness detection

### Milestone 5: Utilities and Polish (Week 5)
- ✅ `contextgit next-id` command
- ✅ `contextgit fmt` command
- ✅ Error handling and validation
- ✅ JSON output for all commands

### Milestone 6: Documentation and Packaging (Week 6)
- ✅ README.md and user guide
- ✅ Example project
- ✅ PyPI packaging
- ✅ Contributing guidelines
- ✅ Testing and bug fixes

---

## Release Criteria for MVP

The MVP is ready for release when:

1. ✅ All MVP-scoped commands are implemented and tested
2. ✅ All functional requirements (FR-1 through FR-13) are met
3. ✅ All non-functional requirements (NFR-1 through NFR-8) are met
4. ✅ Documentation is complete and reviewed
5. ✅ Example project demonstrates end-to-end workflow
6. ✅ Unit tests cover > 80% of code
7. ✅ Integration tests validate all user stories
8. ✅ Performance benchmarks meet targets (< 5s for 1000 files)
9. ✅ Package is installable via `pip install contextgit`
10. ✅ At least 3 external users have tested and provided feedback

---

## Post-MVP: Gathering Feedback

After MVP release, the team should:

1. **Gather user feedback**:
   - Set up GitHub Discussions
   - Monitor issues and feature requests
   - Conduct user interviews

2. **Track metrics**:
   - Installation count (PyPI downloads)
   - GitHub stars and forks
   - Active users (estimated via GitHub activity)

3. **Iterate quickly**:
   - Fix critical bugs within 48 hours
   - Release minor improvements weekly
   - Prioritize Phase 2 features based on user demand

4. **Build community**:
   - Respond to issues promptly
   - Merge quality PRs
   - Highlight community contributions

---

## Summary

The contextgit MVP is tightly scoped to deliver maximum value with minimal complexity:

**In Scope:**
- Core CLI commands for initialization, scanning, querying, and traceability
- LLM-friendly JSON output and fast context extraction
- Git-friendly YAML storage with deterministic formatting
- Local-first, no network dependencies
- Comprehensive documentation

**Out of Scope:**
- VS Code extension (Phase 2)
- Code parsing (Phase 3)
- Web dashboard (Phase 4+)
- Enterprise features (Phase 5+)

This focus ensures the MVP can be built quickly, validated with real users, and iterated based on feedback. Future phases will build on the solid foundation of the MVP to add advanced features and ecosystem integrations.
