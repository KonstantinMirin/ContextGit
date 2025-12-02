# Software Architecture Document

## 1. Introduction

### 1.1 Purpose
This document defines the detailed software architecture for contextgit, a CLI tool for managing requirements traceability in LLM-assisted software projects. It builds upon the high-level architecture in `docs/04_architecture_overview.md` with concrete implementation details.

### 1.2 Scope
This architecture document covers:
- Modular decomposition of the system
- Directory structure and file organization
- Module responsibilities and boundaries
- Interface definitions between modules
- Implementation technology choices
- Key design patterns

### 1.3 Design Goals
1. **Modularity**: Each module has a single, well-defined responsibility
2. **Testability**: Modules can be tested in isolation
3. **Maintainability**: Clear interfaces and minimal coupling
4. **Performance**: Efficient algorithms and data structures
5. **Reliability**: Atomic operations and graceful error handling

---

## 2. Module Hierarchy

The system is organized into four layers with clear dependencies flowing downward:

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Layer                                │
│  - Command definitions (Typer)                              │
│  - Argument parsing and validation                          │
│  - Global error handling                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Application Layer                           │
│  - Command handlers (one per CLI command)                   │
│  - Business logic orchestration                             │
│  - Output formatting coordination                           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Domain Layer                              │
│  Core business logic modules:                               │
│  - Index Manager         - Linking Engine                   │
│  - Metadata Parser       - Checksum Calculator              │
│  - Location Resolver     - ID Generator                     │
│  - Snippet Extractor     - Config Manager                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                Infrastructure Layer                          │
│  - File system operations                                   │
│  - YAML serialization                                       │
│  - Output formatting (text/JSON)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
contextgit/
├── contextgit/                   # Main package
│   ├── __init__.py               # Package initialization, version info
│   ├── __main__.py               # Entry point for python -m contextgit
│   │
│   ├── cli/                      # CLI Layer
│   │   ├── __init__.py
│   │   ├── app.py                # Main Typer app definition
│   │   ├── commands.py           # Command definitions (init, scan, show, etc.)
│   │   └── decorators.py         # Common decorators (error handling, etc.)
│   │
│   ├── handlers/                 # Application Layer
│   │   ├── __init__.py
│   │   ├── base.py               # Base handler with common functionality
│   │   ├── init_handler.py       # contextgit init
│   │   ├── scan_handler.py       # contextgit scan
│   │   ├── status_handler.py     # contextgit status
│   │   ├── show_handler.py       # contextgit show
│   │   ├── extract_handler.py    # contextgit extract
│   │   ├── link_handler.py       # contextgit link
│   │   ├── confirm_handler.py    # contextgit confirm
│   │   ├── next_id_handler.py    # contextgit next-id
│   │   ├── relevant_handler.py   # contextgit relevant-for-file
│   │   └── fmt_handler.py        # contextgit fmt
│   │
│   ├── domain/                   # Domain Layer
│   │   ├── __init__.py
│   │   │
│   │   ├── index/                # Index management module
│   │   │   ├── __init__.py
│   │   │   ├── manager.py        # IndexManager class
│   │   │   ├── validator.py      # Index validation logic
│   │   │   └── sorter.py         # Deterministic sorting
│   │   │
│   │   ├── metadata/             # Metadata parsing module
│   │   │   ├── __init__.py
│   │   │   ├── parser.py         # MetadataParser class
│   │   │   ├── frontmatter.py    # YAML frontmatter parsing
│   │   │   ├── inline.py         # Inline HTML comment parsing
│   │   │   └── validator.py      # Metadata validation
│   │   │
│   │   ├── location/             # Location resolution module
│   │   │   ├── __init__.py
│   │   │   ├── resolver.py       # LocationResolver class
│   │   │   ├── markdown.py       # Markdown structure parser
│   │   │   └── snippet.py        # SnippetExtractor class
│   │   │
│   │   ├── linking/              # Linking and graph module
│   │   │   ├── __init__.py
│   │   │   ├── engine.py         # LinkingEngine class
│   │   │   ├── graph.py          # Graph traversal algorithms
│   │   │   ├── sync.py           # Sync status management
│   │   │   └── orphan.py         # Orphan detection
│   │   │
│   │   ├── checksum/             # Checksum calculation module
│   │   │   ├── __init__.py
│   │   │   └── calculator.py     # ChecksumCalculator class
│   │   │
│   │   ├── id_gen/               # ID generation module
│   │   │   ├── __init__.py
│   │   │   └── generator.py      # IDGenerator class
│   │   │
│   │   └── config/               # Configuration module
│   │       ├── __init__.py
│   │       └── manager.py        # ConfigManager class
│   │
│   ├── infra/                    # Infrastructure Layer
│   │   ├── __init__.py
│   │   ├── filesystem.py         # File I/O abstraction
│   │   ├── yaml_io.py            # YAML serialization
│   │   └── output.py             # Output formatting (text/JSON)
│   │
│   ├── models/                   # Data models (used across layers)
│   │   ├── __init__.py
│   │   ├── node.py               # Node dataclass
│   │   ├── link.py               # Link dataclass
│   │   ├── index.py              # Index dataclass
│   │   ├── config.py             # Config dataclass
│   │   ├── location.py           # Location types
│   │   └── enums.py              # Enums (node types, statuses, etc.)
│   │
│   ├── exceptions.py             # Custom exception types
│   └── constants.py              # Constants (file paths, defaults, etc.)
│
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests (one file per module)
│   │   ├── test_index_manager.py
│   │   ├── test_metadata_parser.py
│   │   ├── test_location_resolver.py
│   │   ├── test_linking_engine.py
│   │   ├── test_checksum_calculator.py
│   │   ├── test_id_generator.py
│   │   └── test_config_manager.py
│   │
│   ├── integration/              # Integration tests
│   │   ├── test_scan_workflow.py
│   │   ├── test_extract_workflow.py
│   │   └── test_linking_workflow.py
│   │
│   ├── e2e/                      # End-to-end tests
│   │   ├── test_cli_init.py
│   │   ├── test_cli_scan.py
│   │   └── test_full_workflow.py
│   │
│   └── fixtures/                 # Test fixtures
│       ├── sample_repo/
│       └── test_data.py
│
├── docs/                         # Existing planning docs
├── design/                       # Design documents (this file)
├── examples/                     # Example projects
├── pyproject.toml                # Project configuration
├── README.md
└── LICENSE
```

---

## 4. Module Specifications

### 4.1 CLI Layer (`cli/`)

**Purpose**: Parse command-line arguments and route to handlers

**Modules**:
- `app.py`: Main Typer application with global options
- `commands.py`: Command definitions (one function per command)
- `decorators.py`: Error handling, logging decorators

**Key Design Decisions**:
- Use Typer for type-safe CLI with automatic help generation
- All commands call corresponding handlers in application layer
- Global exception handler converts exceptions to error messages + exit codes
- No business logic in CLI layer (pure routing)

**External Dependencies**:
- `typer`: CLI framework
- `rich`: Terminal output formatting

---

### 4.2 Application Layer (`handlers/`)

**Purpose**: Orchestrate domain layer modules to implement command logic

**Modules**:
- `base.py`: BaseHandler with common functionality (repo root detection, index loading)
- One handler per command (e.g., `scan_handler.py`)

**Key Design Decisions**:
- Each handler is independent (can be tested separately)
- Handlers coordinate multiple domain modules
- Handlers are responsible for:
  - Loading index/config
  - Calling domain logic
  - Formatting output
  - Saving changes
- Handlers do NOT contain domain logic (delegate to domain layer)

**Common Handler Pattern**:
```python
class ScanHandler(BaseHandler):
    def __init__(self, filesystem, yaml_io, output_formatter):
        self.fs = filesystem
        self.yaml = yaml_io
        self.formatter = output_formatter

    def handle(self, path: str, recursive: bool, dry_run: bool, format: str):
        # 1. Load dependencies
        config = ConfigManager(self.fs, self.yaml).load()
        index = IndexManager(self.fs, self.yaml).load_index()

        # 2. Execute domain logic
        files = self.fs.walk_files(path, "*.md", recursive)
        parser = MetadataParser()
        # ... coordinate parsing, updating index, etc.

        # 3. Format output
        result = self.formatter.format_scan_result(summary, format)
        return result
```

---

### 4.3 Domain Layer (`domain/`)

**Purpose**: Core business logic, independent of CLI and I/O

#### 4.3.1 Index Module (`domain/index/`)

**Classes**:
- `IndexManager`: CRUD operations for nodes and links
- `IndexValidator`: Validate index structure
- `IndexSorter`: Deterministic sorting

**Responsibilities**:
- Load/save index file atomically
- Add/update/delete nodes and links
- Validate structure before saving
- Sort nodes by ID, links by (from, to)

**Key Interface**:
```python
class IndexManager:
    def load_index() -> Index
    def save_index(index: Index) -> None
    def get_node(id: str) -> Node | None
    def add_node(node: Node) -> None
    def update_node(id: str, updates: dict) -> None
    def delete_node(id: str) -> None
    def add_link(link: Link) -> None
    def get_links_from(node_id: str) -> list[Link]
    def get_links_to(node_id: str) -> list[Link]
```

---

#### 4.3.2 Metadata Module (`domain/metadata/`)

**Classes**:
- `MetadataParser`: Main parser interface
- `FrontmatterParser`: Parse YAML frontmatter
- `InlineParser`: Parse HTML comment blocks
- `MetadataValidator`: Validate metadata fields

**Responsibilities**:
- Extract metadata from Markdown files
- Support both frontmatter and inline formats
- Validate required/optional fields
- Handle `id: auto` placeholder

**Key Interface**:
```python
class MetadataParser:
    def parse_file(file_path: str) -> list[RawMetadata]
    def parse_frontmatter(content: str) -> RawMetadata | None
    def parse_inline_blocks(content: str) -> list[RawMetadata]
    def validate_metadata(raw: RawMetadata) -> Metadata
```

---

#### 4.3.3 Location Module (`domain/location/`)

**Classes**:
- `LocationResolver`: Map metadata to locations in file
- `MarkdownParser`: Parse Markdown structure (headings)
- `SnippetExtractor`: Extract text snippets

**Responsibilities**:
- Parse Markdown to identify heading hierarchy
- Resolve metadata block location (heading path or line range)
- Extract snippets by location

**Key Interface**:
```python
class LocationResolver:
    def resolve_location(file_path: str, metadata_line: int) -> Location

class SnippetExtractor:
    def extract_snippet(file_path: str, location: Location) -> str
```

---

#### 4.3.4 Linking Module (`domain/linking/`)

**Classes**:
- `LinkingEngine`: Main linking operations
- `GraphTraverser`: Graph traversal algorithms
- `SyncStatusManager`: Update sync status
- `OrphanDetector`: Detect orphan nodes

**Responsibilities**:
- Build links from metadata upstream/downstream
- Traverse graph (upstream/downstream queries)
- Detect checksum changes and update sync status
- Identify orphan nodes
- Detect circular dependencies

**Key Interface**:
```python
class LinkingEngine:
    def build_links_from_metadata(nodes: dict[str, Node]) -> list[Link]
    def update_sync_status(index: Index, changed_nodes: set[str]) -> None
    def get_upstream_nodes(node_id: str, depth: int) -> list[Node]
    def get_downstream_nodes(node_id: str, depth: int) -> list[Node]
    def detect_orphans(index: Index) -> tuple[list[str], list[str]]
```

---

#### 4.3.5 Checksum Module (`domain/checksum/`)

**Classes**:
- `ChecksumCalculator`: Calculate and compare checksums

**Responsibilities**:
- Normalize text (strip whitespace, normalize line endings)
- Calculate SHA-256 hash
- Compare checksums

**Key Interface**:
```python
class ChecksumCalculator:
    def calculate_checksum(text: str) -> str
    def compare_checksums(old: str, new: str) -> bool
```

---

#### 4.3.6 ID Generation Module (`domain/id_gen/`)

**Classes**:
- `IDGenerator`: Generate next sequential ID

**Responsibilities**:
- Read prefix from config
- Scan existing IDs
- Generate next ID with zero-padding

**Key Interface**:
```python
class IDGenerator:
    def next_id(node_type: str, index: Index, config: Config) -> str
```

---

#### 4.3.7 Config Module (`domain/config/`)

**Classes**:
- `ConfigManager`: Load/save config

**Responsibilities**:
- Load config from `.contextgit/config.yaml`
- Provide defaults for missing fields
- Validate config structure

**Key Interface**:
```python
class ConfigManager:
    def load_config() -> Config
    def save_config(config: Config) -> None
    def get_default_config() -> Config
```

---

### 4.4 Infrastructure Layer (`infra/`)

**Purpose**: Abstract external dependencies (file I/O, YAML, output)

**Modules**:
- `filesystem.py`: File system operations
- `yaml_io.py`: YAML serialization
- `output.py`: Output formatting

**Key Design Decisions**:
- All file I/O goes through `filesystem.py` (enables mocking in tests)
- YAML serialization is deterministic (sorted keys, consistent formatting)
- Output formatter supports both text and JSON

**Key Interfaces**:
```python
# filesystem.py
class FileSystem:
    def read_file(path: str) -> str
    def write_file_atomic(path: str, content: str) -> None
    def walk_files(root: str, pattern: str, recursive: bool) -> Iterator[str]
    def find_repo_root(start_path: str) -> str

# yaml_io.py
class YAMLSerializer:
    def load_yaml(content: str) -> dict
    def dump_yaml(data: dict) -> str

# output.py
class OutputFormatter:
    def format_status(index: Index, format: str) -> str
    def format_node(node: Node, format: str) -> str
    def format_scan_result(summary: dict, format: str) -> str
```

---

### 4.5 Models (`models/`)

**Purpose**: Define data structures used across all layers

**Modules**:
- `node.py`: Node dataclass
- `link.py`: Link dataclass
- `index.py`: Index dataclass
- `config.py`: Config dataclass
- `location.py`: Location types (HeadingLocation, LineLocation)
- `enums.py`: Enums (NodeType, NodeStatus, RelationType, SyncStatus)

**Key Design Decisions**:
- Use Python dataclasses with type hints
- Immutable by default (use `frozen=True` where possible)
- Include validation in `__post_init__` methods
- All timestamps are ISO 8601 strings

---

## 5. Key Design Patterns

### 5.1 Dependency Injection

Handlers receive dependencies via constructor injection:

```python
class ScanHandler:
    def __init__(
        self,
        filesystem: FileSystem,
        yaml_io: YAMLSerializer,
        output_formatter: OutputFormatter,
        index_manager: IndexManager,
        metadata_parser: MetadataParser,
        # ... other dependencies
    ):
        self.fs = filesystem
        self.yaml = yaml_io
        # ...
```

**Benefits**:
- Testable (inject mocks)
- Flexible (swap implementations)
- Explicit dependencies

---

### 5.2 Atomic File Writes

All file writes use the "write to temp, then rename" pattern:

```python
def write_file_atomic(path: str, content: str):
    temp_path = path + ".tmp"
    with open(temp_path, 'w') as f:
        f.write(content)
    os.rename(temp_path, path)  # Atomic on POSIX
```

**Benefits**:
- Never corrupt index file
- Safe even if process crashes mid-write

---

### 5.3 Repository Root Detection

All commands auto-detect repository root by looking for `.contextgit/` or `.git/`:

```python
def find_repo_root(start_path: str) -> str:
    current = os.path.abspath(start_path)
    while current != '/':
        if os.path.exists(os.path.join(current, '.contextgit')):
            return current
        if os.path.exists(os.path.join(current, '.git')):
            return current
        current = os.path.dirname(current)
    raise RepoNotFoundError("Not in a contextgit repository")
```

---

### 5.4 Error Handling Strategy

**Custom Exceptions** (defined in `exceptions.py`):
```python
class ContextGitError(Exception):
    """Base exception for all contextgit errors"""
    exit_code = 1

class RepoNotFoundError(ContextGitError):
    exit_code = 1

class NodeNotFoundError(ContextGitError):
    exit_code = 3

class InvalidMetadataError(ContextGitError):
    exit_code = 4

class IndexCorruptedError(ContextGitError):
    exit_code = 5
```

**Global Exception Handler** (in CLI layer):
```python
@app.callback()
def main(ctx: typer.Context):
    try:
        # Execute command
        pass
    except ContextGitError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=e.exit_code)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(code=1)
```

---

## 6. Data Flow Examples

### 6.1 Scan Command Data Flow

```
1. CLI Layer (commands.py)
   ↓ parse arguments

2. ScanHandler.handle(path, recursive, dry_run, format)
   ↓
   ├─→ FileSystem.find_repo_root() → repo_root
   ├─→ ConfigManager.load_config() → config
   ├─→ IndexManager.load_index() → old_index
   ├─→ FileSystem.walk_files(path, "*.md", recursive) → files
   │
   ├─→ For each file:
   │   ├─→ FileSystem.read_file(file) → content
   │   ├─→ MetadataParser.parse_file(file) → metadata_blocks
   │   │
   │   ├─→ For each metadata_block:
   │   │   ├─→ LocationResolver.resolve_location() → location
   │   │   ├─→ SnippetExtractor.extract_snippet() → snippet
   │   │   ├─→ ChecksumCalculator.calculate_checksum(snippet) → checksum
   │   │   └─→ Create/update Node
   │   │
   │   └─→ LinkingEngine.build_links_from_metadata() → new_links
   │
   ├─→ LinkingEngine.update_sync_status(changed_nodes) → updated_links
   │
   ├─→ IndexManager.save_index(new_index) [unless dry_run]
   │
   └─→ OutputFormatter.format_scan_result(summary, format) → output
   ↓

3. CLI Layer: print output, exit
```

---

### 6.2 Extract Command Data Flow

```
1. CLI Layer (commands.py)
   ↓ parse arguments

2. ExtractHandler.handle(id, format)
   ↓
   ├─→ FileSystem.find_repo_root() → repo_root
   ├─→ IndexManager.load_index() → index
   ├─→ IndexManager.get_node(id) → node [or raise NodeNotFoundError]
   │
   ├─→ SnippetExtractor.extract_snippet(node.file, node.location) → snippet
   │
   └─→ OutputFormatter.format_extract_result(node, snippet, format) → output
   ↓

3. CLI Layer: print output, exit
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

Test each domain module in isolation with mocked dependencies:

```python
def test_index_manager_add_node(tmp_path):
    # Setup
    fs = MockFileSystem(tmp_path)
    yaml = YAMLSerializer()
    manager = IndexManager(fs, yaml)

    # Execute
    node = Node(id="SR-001", type="system", title="Test", ...)
    manager.add_node(node)

    # Verify
    retrieved = manager.get_node("SR-001")
    assert retrieved == node
```

---

### 7.2 Integration Tests

Test workflows involving multiple modules:

```python
def test_scan_and_extract_workflow(sample_repo):
    # Setup
    repo_root = sample_repo  # fixture with sample files

    # Scan
    handler = ScanHandler(...)
    handler.handle(path=repo_root / "docs", recursive=True, ...)

    # Verify index updated
    index = IndexManager(...).load_index()
    assert "SR-001" in index.nodes

    # Extract
    extract_handler = ExtractHandler(...)
    snippet = extract_handler.handle(id="SR-001", format="text")
    assert "system requirement text" in snippet
```

---

### 7.3 End-to-End Tests

Test CLI commands directly:

```python
def test_cli_scan_command(sample_repo, cli_runner):
    result = cli_runner.invoke(app, ["scan", "docs", "--recursive"])
    assert result.exit_code == 0
    assert "Scanned" in result.stdout
```

---

## 8. Performance Considerations

### 8.1 Index Loading

- Load index once per command invocation
- Build in-memory lookup maps:
  - `nodes_by_id: dict[str, Node]` for O(1) node lookup
  - `links_by_from: dict[str, list[Link]]` for O(1) upstream queries
  - `links_by_to: dict[str, list[Link]]` for O(1) downstream queries

### 8.2 File Scanning

- Use `os.walk` for directory traversal
- Process files sequentially (parallel processing in future)
- Stream file reading (don't load entire file into memory)

### 8.3 Checksum Calculation

- Cache checksums in index (only recalculate on content change)
- Use SHA-256 (fast, standard, collision-resistant)

---

## 9. Security Considerations

### 9.1 Path Validation

Always validate that file paths are within repository root:

```python
def validate_path(path: str, repo_root: str) -> str:
    abs_path = os.path.abspath(path)
    abs_repo = os.path.abspath(repo_root)
    if not abs_path.startswith(abs_repo):
        raise SecurityError(f"Path {path} is outside repository")
    return abs_path
```

### 9.2 YAML Safety

Use safe YAML loading (no code execution):

```python
yaml.safe_load(content)  # NOT yaml.load()
```

---

## 10. Future Extensibility

While maintaining MVP scope, the architecture supports future enhancements:

### 10.1 Additional File Formats

Add parsers for ReStructuredText, AsciiDoc:

```python
# domain/metadata/rst_parser.py
class RSTParser(MetadataParser):
    def parse_file(file_path: str) -> list[RawMetadata]:
        # Parse RST-specific metadata format
        pass
```

### 10.2 Code File Parsing

Add parsers for source code comments:

```python
# domain/metadata/code_parser.py
class PythonDocstringParser(MetadataParser):
    def parse_file(file_path: str) -> list[RawMetadata]:
        # Extract metadata from docstrings
        pass
```

### 10.3 Watch Mode

Add file system watcher for automatic re-scanning:

```python
# domain/watcher/file_watcher.py
class FileWatcher:
    def watch(path: str, on_change: Callable):
        # Use watchdog or inotify
        pass
```

---

## 11. Summary

This architecture provides:

1. **Clear Module Boundaries**: Each module has a single responsibility
2. **Testability**: All modules can be tested in isolation
3. **Maintainability**: Dependencies flow downward, interfaces are explicit
4. **Performance**: Efficient algorithms and data structures
5. **Reliability**: Atomic operations, clear error handling
6. **Extensibility**: Easy to add new features without breaking existing code

The modular design ensures that contextgit is maintainable, testable, and ready for future enhancements while meeting all MVP requirements.
