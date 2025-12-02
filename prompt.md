
You are an expert software architect and senior Python developer. Your task is to help me design an open-source MVP tool, and in this first phase you must ONLY produce detailed planning and requirements documents (no code).

====================================
PRODUCT CONTEXT & GOAL
====================================

We are designing an open-source tool (working name: `contextgit`) with these characteristics:

- Linux-first CLI tool, written in Python.
- Git-friendly: all state is stored in plain text (YAML/Markdown) in the repository.
- Its purpose is to manage **requirements and context traceability** for projects that use LLMs (especially Claude Code) to generate and maintain:
  - business requirements
  - system requirements
  - software architecture docs
  - design docs
  - code-level specs
  - links to code and tests

The core problem:
- When using LLMs to build products, people generate lots of context documents (requirements, specs, designs), but:
  - It’s hard to know which document is the latest or authoritative.
  - It’s hard to maintain **traceability** between layers (business → system → architecture → code → tests).
  - It’s hard to detect when upstream requirements change and downstream docs/code are not updated.
  - Context gets stale and LLMs start using outdated documents, causing incorrect or inconsistent output.

The tool will:
- Treat requirements and design/context pieces as first-class **nodes** with IDs and metadata.
- Track **links** (upstream/downstream relationships) between these nodes.
- Keep a **central index** (YAML) of all nodes and links.
- Provide CLI commands to:
  - scan docs and update the index
  - show traceability
  - detect stale/changed requirements
  - extract only relevant snippets for LLMs
  - help LLM-aware workflows focus on the right context instead of whole files.

The MVP MUST:
- Be usable entirely locally on Linux (no cloud backend).
- Provide a Python CLI (e.g. with Typer or Click).
- Be easy to integrate with Claude Code and other LLM CLIs.
- Be open source–ready: clear docs, clear structure, sensible defaults.

====================================
LLM INTEGRATION PRINCIPLES
====================================

The tool is designed to work especially well with LLM CLIs (Claude Code, etc.).

Key conventions:

1. **Project marker**
   - A project uses this tool if and only if it has:
     - `.contextgit/config.yaml` in its root.
   - When an LLM sees this file, it should:
     - Treat the repo as “contextgit-managed”.
     - Assume `contextgit` CLI is available.
     - Add/update metadata blocks in any requirements/design docs it generates.

2. **Inline metadata for requirements & context**
   - Requirements and design items are represented inside documents via structured metadata blocks, either:
     - YAML frontmatter at the top of a file, or
     - Small embedded comment blocks near each requirement.

   Example (YAML frontmatter style):

   ```markdown
   ---
   contextgit:
     id: SR-010
     type: system
     title: "System shall expose job execution logs via API"
     upstream: [BR-001]
     downstream: [AR-020, C-120]
   ---
   # System Design – Logging

   ...

Example (inline comment block for section-level requirement):

```markdown
## 3.1 Logging API

<!-- contextgit
id: SR-010
type: system
title: "System shall expose job execution logs via API"
upstream: [BR-001]
downstream: [AR-020]
-->

The system shall expose job execution logs via a REST API ...
```

Where:

* `id` = unique node tag (e.g. `BR-001`, `SR-010`, `AR-020`, `C-120`).
* `type` = node type (e.g. `business`, `system`, `architecture`, `code`, `test`, `decision`).
* `title` = short human-readable title of the requirement/context item.
* `upstream` = list of IDs that this item refines or depends on.
* `downstream` = list of IDs that implement or test this item.

3. **ID conventions**

   * Configuration file `.contextgit/config.yaml` defines prefixes per type, e.g.:

     ```yaml
     tag_prefixes:
       business_requirement: "BR-"
       system_requirement: "SR-"
       software_requirement: "AR-"
       code_item: "C-"
       test_item: "T-"
       decision: "ADR-"
     ```

   * The CLI is responsible for generating new IDs, keeping them unique and ordered.

   * An LLM should either:

     * Call `contextgit next-id <type>` (conceptually), or
     * Use a placeholder (`id: auto`) and then rely on `contextgit scan` to assign and write real IDs.

4. **Location tracking**

   * The index must know where in a file each node lives.
   * `location` can be:

     * Heading path (e.g. `[ "System Design – Logging", "3.1 Logging API" ]`)
     * Line range (start/end)
   * This allows the CLI to **extract only the relevant snippets** instead of reading entire files.

5. **LLM-friendly commands**

   * All read-oriented CLI commands must support `--format json` so they can be consumed programmatically by LLM tools (including Claude Code).
   * LLM workflows should:

     * Use the CLI to discover relevant requirement IDs.
     * Use the CLI to extract only the snippets they need.
     * Avoid loading entire documents into context when not needed.

====================================
DATA MODEL (MVP)
================

We need a clear data model for the MVP:

1. Node (requirement/context item):

   * `id`: string (e.g. "SR-010")
   * `type`: enum (business | system | architecture | code | test | decision | other)
   * `title`: short string
   * `file`: path to file (relative to repo root)
   * `location`: location descriptor (heading path OR line range)
   * `status`: enum (draft | active | deprecated | superseded)
   * `llm_generated`: boolean (was this created by an LLM?)
   * `last_updated`: timestamp (ISO 8601 string)
   * `checksum`: string (hash of the main text snippet, used to detect changes)
   * Optional extra metadata:

     * `tags`: list of strings (e.g. "feature:logging", "domain:billing")

2. Link (traceability relationship):

   * `from`: node id (e.g. "BR-001")
   * `to`: node id (e.g. "SR-010")
   * `relation_type`: enum (refines | implements | tests | derived_from | depends_on)
   * `sync_status`: enum:

     * `ok`
     * `upstream_changed`
     * `downstream_changed`
     * `broken`
   * `last_checked`: timestamp
   * Internally, the tool should store the last-known `checksum` pairs for both sides to detect drift.

3. Central index file:

   * Located at `.contextgit/requirements_index.yaml`

   * Structure:

     ```yaml
     nodes:
       - id: BR-001
         type: business
         title: "Cron jobs must be observable"
         file: docs/01_business/requirements.md
         location:
           kind: heading
           path: ["Business Requirements", "Observability"]
         status: active
         llm_generated: true
         last_updated: "2025-12-02T17:00:00Z"
         checksum: "abc123..."
         tags: ["feature:observability"]

       - id: SR-010
         type: system
         title: "System shall expose job execution logs via API"
         file: docs/02_system_design/logging.md
         location:
           kind: heading
           path: ["System Design – Logging", "3.1 Logging API"]
         status: active
         llm_generated: false
         last_updated: "2025-12-02T18:00:00Z"
         checksum: "def456..."
         tags: ["feature:observability"]

     links:
       - from: BR-001
         to: SR-010
         relation_type: refines
         sync_status: ok
         last_checked: "2025-12-02T18:05:00Z"
     ```

   * The CLI must preserve deterministic ordering to keep git diffs clean.

====================================
CLI FEATURES (MVP)
==================

The Python CLI (`contextgit`, Linux-first) should support at least the following commands in the MVP:

1. `contextgit init`

   * Initialize a repo for contextgit.
   * Create `.contextgit/config.yaml` with default settings.
   * Create an empty `.contextgit/requirements_index.yaml`.
   * Optionally ask interactively for:

     * layer directories (business, system, architecture, code, tests)
     * tag prefixes

2. `contextgit scan [PATH] [--recursive]`

   * Scan the given file or directory for `contextgit` metadata blocks in Markdown or other supported formats.
   * Create or update corresponding nodes in the index.
   * Create or update links from `upstream` and `downstream` fields.
   * Recalculate checksums and update `sync_status` for links:

     * If upstream changed: `sync_status = upstream_changed`
     * If downstream changed: `sync_status = downstream_changed`
     * If both updated and later confirmed: `sync_status = ok`
   * Supports:

     * `--format json` for reporting what changed.
     * `--dry-run` to only show changes without writing the index.

3. `contextgit status`

   * Show overall project health:

     * Number of nodes by type
     * Number of links
     * Count of stale links
     * Count of orphan nodes (no upstream and/or no downstream)
   * Options:

     * `--orphans`
     * `--stale`
     * `--file <path>`
     * `--type <type>`
     * `--format json`

4. `contextgit show <ID>`

   * Display details about a specific node:

     * metadata
     * upstream links
     * downstream links
   * Options:

     * `--format json`
     * `--graph` (print a small text graph or adjacency list)

5. `contextgit extract <ID>`

   * Print only the snippet of the file corresponding to the given node ID, using the stored `location`.
   * Options:

     * `--format json` with fields { id, file, snippet }

   This is critical for LLMs so they can work with **just** the relevant requirement instead of the whole file.

6. `contextgit link <FROM_ID> <TO_ID> --type <relation_type>`

   * Manually create or update a link.
   * Example relation types: `refines`, `implements`, `tests`, `depends_on`.

7. `contextgit confirm <ID>`

   * Mark links involving this ID as “confirmed in sync” after you have manually updated downstream artifacts.
   * This updates `sync_status` to `ok` and updates stored checksums.

8. `contextgit next-id <type>`

   * Generate the next available ID for a given type, using the prefix rules from config.
   * Output just the new ID (e.g. `SR-012`), or JSON if `--format json`.
   * This is used by tools/LLMs to assign new IDs.

9. `contextgit relevant-for-file <path>`

   * Return the IDs of nodes that are directly linked to that file or are tagged as relevant to it.
   * Used by LLMs when working on a specific source file to fetch only related requirements.

10. `contextgit fmt`

    * Normalize and pretty-print the index file:

      * sort nodes by ID
      * sort links
    * For stable git diffs.

All commands that output data must support `--format json` for machine consumption.

====================================
VS CODE / UI (MVP SCOPE)
========================

For MVP we only need **requirements for the UI**, not implementation:

* A basic VS Code extension (not necessarily implemented in code yet) that can:

  * Read `.contextgit/requirements_index.yaml`.
  * Show a side panel with:

    * Nodes grouped by type.
    * Icons or badges for:

      * `stale` links
      * `orphan` nodes
  * Allow clicking a node to open the corresponding file at its location.
  * Provide a command “Show traceability for current file” that:

    * Lists all related node IDs using `contextgit relevant-for-file`.
    * Shows upstream and downstream items for each.

Future non-MVP idea (only mention briefly in requirements for future work):

* Graph visualization using a webview.
* More advanced filters and search.

====================================
NON-FUNCTIONAL REQUIREMENTS (MVP)
=================================

* Language: Python 3.11+.
* Target OS: Linux first; should also run on macOS and Windows if possible, but Linux is the priority.
* Packaging:

  * Installable via `pip` (e.g. `pip install contextgit`).
  * Simple, minimal dependencies.
* Performance:

  * Should handle a few thousand nodes and links without noticeable lag.
  * Index operations should be O(N log N) or better.
* Reliability:

  * Never corrupt the index file; use temporary files and atomic renames.
  * Provide clear error messages on malformed metadata blocks.
* Git-friendliness:

  * Deterministic ordering of YAML.
  * Human-readable diffs.
* Open-source-ready:

  * Clear LICENSE (e.g. Apache 2.0 or MIT).
  * `README.md` explaining core concepts with examples.
  * Example project demonstrating usage with Markdown docs and simple code.

====================================
PHASE 1 TASK FOR YOU (CLAUDE) – IMPORTANT
=========================================

In THIS phase, DO NOT write any Python code yet.

Instead, produce a set of **planning and requirements documents** in Markdown that fully describe the MVP. Structure them as if they were files in a `docs/` directory.

I want at least the following documents, in this order:

1. `docs/01_product_overview.md`

   * Problem statement
   * Target users
   * Goals and non-goals of the tool
   * High-level feature list (MVP only)
   * Future extensions (brief)

2. `docs/02_user_stories.md`

   * Developer personas:

     * Solo dev using Claude CLI and git
     * Small team using git and CI
   * Concrete user stories capturing:

     * Creating requirements
     * Linking business → system → architecture → code
     * Detecting stale requirements
     * Using the tool from an LLM CLI
   * Focus on realistic flows.

3. `docs/03_system_requirements.md`

   * Functional requirements (detailed, numbered “shall” style if possible).
   * Non-functional requirements (performance, reliability, UX, integration).
   * Explicit constraints: local-first, git-friendly, LLM-integration-focused.

4. `docs/04_architecture_overview.md`

   * High-level architecture of the CLI tool.
   * Description of main components:

     * CLI layer
     * Parsing/scan layer
     * Index manager
     * Linking engine (sync status, checksum tracking)
     * Location resolver and snippet extractor
   * How the CLI commands interact with the index.
   * How the tool will integrate with LLMs conceptually.

5. `docs/05_data_model_and_file_layout.md`

   * Detailed schema for:

     * Node structure
     * Link structure
     * Config file (`.contextgit/config.yaml`)
     * Index file (`.contextgit/requirements_index.yaml`)
   * Examples of actual YAML structures.
   * Recommended repository directory layout (docs, src, .contextgit).

6. `docs/06_cli_specification.md`

   * Detailed specification for each MVP command:

     * Arguments
     * Options
     * Inputs and outputs (including JSON output schema)
     * Error conditions
     * Examples
   * This should be precise enough that a developer could implement the CLI later.

7. `docs/07_llm_integration_guidelines.md`

   * How Claude CLI and other LLM tools should interact with the project:

     * How to detect `.contextgit/config.yaml`.
     * How to use `contextgit next-id`, `scan`, `show`, `extract`, `relevant-for-file`.
     * Examples of workflows:

       * “Update requirement SR-010”
       * “Implement code for SR-010”
       * “Review requirements relevant to src/logging/api.py”
   * Clear, step-by-step examples tailored for LLM-driven workflows.

8. `docs/08_mvp_scope_and_future_work.md`

   * Explicit list of what is IN scope for the MVP.
   * Explicit list of what is OUT of scope for the MVP (e.g. cloud backend, SaaS dashboard, advanced graphs, enterprise features).
   * Roadmap notes for future versions (but clearly separated from MVP).

Formatting guidelines:

* Use clear headings and subheadings.
* Use bullet lists where helpful.
* Use numbered requirements where appropriate (e.g. `REQ-001`, `REQ-002` inside the docs, separate from node IDs like `SR-010`).
* Keep everything in clean Markdown.

Repeat: In this phase, generate ONLY these planning documents. Do NOT generate Python code or implementation yet.

Start now by outputting the content of these documents in order, separated clearly by headings like:

`=== docs/01_product_overview.md ===`
`=== docs/02_user_stories.md ===`
...

and so on.

```

::contentReference[oaicite:0]{index=0}
```
