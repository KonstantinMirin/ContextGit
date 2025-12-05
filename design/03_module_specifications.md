---
contextgit:
  id: AR-005
  type: architecture
  title: Module specifications and API documentation
  status: active
  upstream:
    - AR-003
  tags: [mvp, modules, api]
---

# Module Specifications

## 1. Introduction

This document provides comprehensive specifications for each module in the contextgit system, including:
- Public API documentation
- Dependencies
- Usage examples
- Testing guidelines
- Performance requirements

---

## 2. Domain Layer Modules

### 2.1 Index Manager Module

**Location**: `contextgit/domain/index/manager.py`

**Purpose**: Manage CRUD operations for the requirements index with atomic file operations.

**Dependencies**:
- `models.index.Index`
- `models.node.Node`
- `models.link.Link`
- `infra.filesystem.FileSystem`
- `infra.yaml_io.YAMLSerializer`
- `exceptions.IndexCorruptedError`
- `exceptions.NodeNotFoundError`

#### 2.1.1 Public API

```python
class IndexManager:
    """Manages CRUD operations for the requirements index."""

    def __init__(
        self,
        filesystem: FileSystem,
        yaml_io: YAMLSerializer,
        repo_root: str
    ):
        """
        Initialize IndexManager.

        Args:
            filesystem: File system abstraction
            yaml_io: YAML serialization handler
            repo_root: Repository root path
        """

    def load_index(self) -> Index:
        """
        Load index from disk. Results are cached in memory.

        Returns:
            Index object with nodes and links

        Raises:
            IndexCorruptedError: If index file is malformed
        """

    def save_index(self, index: Index) -> None:
        """
        Save index to disk atomically.

        Validates index before saving. Uses atomic write (temp + rename).

        Args:
            index: Index to save

        Raises:
            ValueError: If index validation fails
            IOError: If file write fails
        """

    def get_node(self, node_id: str) -> Node:
        """
        Get node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node object

        Raises:
            NodeNotFoundError: If node doesn't exist
        """

    def add_node(self, node: Node) -> None:
        """
        Add a new node to the index.

        Args:
            node: Node to add

        Raises:
            ValueError: If node ID already exists
        """

    def update_node(self, node_id: str, updates: dict) -> None:
        """
        Update an existing node.

        Args:
            node_id: Node to update
            updates: Fields to update (partial)

        Raises:
            NodeNotFoundError: If node doesn't exist
        """

    def delete_node(self, node_id: str) -> None:
        """
        Delete a node from the index.

        Args:
            node_id: Node to delete

        Raises:
            NodeNotFoundError: If node doesn't exist
        """

    def add_link(self, link: Link) -> None:
        """
        Add a new link to the index.

        Validates that both nodes exist.

        Args:
            link: Link to add

        Raises:
            NodeNotFoundError: If either node doesn't exist
            ValueError: If link already exists
        """

    def update_link(self, from_id: str, to_id: str, updates: dict) -> None:
        """
        Update an existing link.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            updates: Fields to update (partial)

        Raises:
            ValueError: If link doesn't exist
        """

    def get_link(self, from_id: str, to_id: str) -> Link | None:
        """
        Get a specific link.

        Args:
            from_id: Source node ID
            to_id: Target node ID

        Returns:
            Link object or None if not found
        """

    def get_links_from(self, node_id: str) -> list[Link]:
        """
        Get all outgoing links from a node.

        Args:
            node_id: Source node ID

        Returns:
            List of outgoing links
        """

    def get_links_to(self, node_id: str) -> list[Link]:
        """
        Get all incoming links to a node.

        Args:
            node_id: Target node ID

        Returns:
            List of incoming links
        """
```

#### 2.1.2 Usage Example

```python
from domain.index.manager import IndexManager
from infra.filesystem import FileSystem
from infra.yaml_io import YAMLSerializer

# Initialize
fs = FileSystem()
yaml = YAMLSerializer()
manager = IndexManager(fs, yaml, repo_root="/path/to/repo")

# Load index
index = manager.load_index()

# Get a node
node = manager.get_node("SR-010")
print(node.title)

# Add a new node
new_node = Node(
    id="SR-020",
    type=NodeType.SYSTEM,
    title="New requirement",
    file="docs/system.md",
    location=HeadingLocation(path=["Section"]),
    status=NodeStatus.ACTIVE,
    last_updated="2025-12-02T10:00:00Z",
    checksum="abc123...",
)
index.nodes["SR-020"] = new_node
manager.save_index(index)
```

#### 2.1.3 Testing Guidelines

**Unit Tests**:
- Test loading empty index
- Test loading valid index
- Test loading corrupted index (should raise error)
- Test adding/updating/deleting nodes
- Test adding/updating links
- Test atomic write behavior (simulate crash during write)

**Performance Requirements**:
- Load index: < 100ms for 5000 nodes
- Save index: < 200ms for 5000 nodes
- Get node by ID: O(1), < 1ms

---

### 2.2 Metadata Parser Module

**Location**: `contextgit/domain/metadata/parser.py`

**Purpose**: Extract contextgit metadata from Markdown files.

**Dependencies**:
- `infra.filesystem.FileSystem`
- `infra.yaml_io.YAMLSerializer`
- `exceptions.InvalidMetadataError`

#### 2.2.1 Public API

```python
@dataclass
class RawMetadata:
    """Raw metadata extracted from file before validation."""
    id: str
    type: str
    title: str
    upstream: list[str]
    downstream: list[str]
    status: str = "active"
    tags: list[str] = field(default_factory=list)
    llm_generated: bool = False
    line_number: int = 0


class MetadataParser:
    """Parses contextgit metadata from Markdown files."""

    def __init__(self, filesystem: FileSystem):
        """
        Initialize MetadataParser.

        Args:
            filesystem: File system abstraction
        """

    def parse_file(self, file_path: str) -> list[RawMetadata]:
        """
        Parse all metadata blocks in a file.

        Supports both YAML frontmatter and inline HTML comments.

        Args:
            file_path: Path to Markdown file

        Returns:
            List of raw metadata blocks found in file

        Raises:
            InvalidMetadataError: If metadata is malformed
            FileNotFoundError: If file doesn't exist
        """
```

#### 2.2.2 Usage Example

```python
from domain.metadata.parser import MetadataParser
from infra.filesystem import FileSystem

fs = FileSystem()
parser = MetadataParser(fs)

# Parse a file
metadata_blocks = parser.parse_file("docs/system/logging.md")

for metadata in metadata_blocks:
    print(f"Found node: {metadata.id} - {metadata.title}")
    print(f"  Upstream: {metadata.upstream}")
    print(f"  Downstream: {metadata.downstream}")
```

#### 2.2.3 Testing Guidelines

**Unit Tests**:
- Test parsing YAML frontmatter
- Test parsing inline HTML comments
- Test parsing file with both frontmatter and inline blocks
- Test parsing file with multiple inline blocks
- Test error handling for malformed YAML
- Test error handling for missing required fields
- Test handling of `id: auto`

**Performance Requirements**:
- Parse file: < 50ms for typical file (< 1000 lines)

---

### 2.3 Location Resolver Module

**Location**: `contextgit/domain/location/resolver.py`

**Purpose**: Map metadata blocks to precise locations in files.

**Dependencies**:
- `infra.filesystem.FileSystem`
- `models.location.Location`

#### 2.3.1 Public API

```python
class LocationResolver:
    """Resolves metadata block locations in Markdown files."""

    def __init__(self, filesystem: FileSystem):
        """
        Initialize LocationResolver.

        Args:
            filesystem: File system abstraction
        """

    def resolve_location(
        self, file_path: str, metadata_line: int
    ) -> Location:
        """
        Resolve location for a metadata block.

        Finds the heading immediately after the metadata block
        and builds the full heading path.

        Args:
            file_path: Path to the Markdown file
            metadata_line: Line number where metadata block starts

        Returns:
            Location object (HeadingLocation or LineLocation)

        Raises:
            FileNotFoundError: If file doesn't exist
        """
```

#### 2.3.2 Usage Example

```python
from domain.location.resolver import LocationResolver
from infra.filesystem import FileSystem

fs = FileSystem()
resolver = LocationResolver(fs)

# Resolve location for metadata block at line 10
location = resolver.resolve_location("docs/system.md", metadata_line=10)

if isinstance(location, HeadingLocation):
    print(f"Location: {' > '.join(location.path)}")
elif isinstance(location, LineLocation):
    print(f"Location: lines {location.start}-{location.end}")
```

#### 2.3.3 Testing Guidelines

**Unit Tests**:
- Test resolving location after top-level heading
- Test resolving location after nested heading
- Test resolving location with no heading after metadata
- Test building correct heading path for deeply nested headings
- Test handling of edge cases (metadata at end of file)

**Performance Requirements**:
- Resolve location: < 10ms for typical file

---

### 2.4 Snippet Extractor Module

**Location**: `contextgit/domain/location/snippet.py`

**Purpose**: Extract text snippets from files based on locations.

**Dependencies**:
- `infra.filesystem.FileSystem`
- `models.location.Location`

#### 2.4.1 Public API

```python
class SnippetExtractor:
    """Extracts text snippets from files based on locations."""

    def __init__(self, filesystem: FileSystem):
        """
        Initialize SnippetExtractor.

        Args:
            filesystem: File system abstraction
        """

    def extract_snippet(self, file_path: str, location: Location) -> str:
        """
        Extract text snippet from file based on location.

        For HeadingLocation: extracts from heading to next same-level heading
        For LineLocation: extracts exact line range

        Args:
            file_path: Path to the file
            location: Location specification

        Returns:
            Extracted text content

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If heading not found or line range invalid
        """
```

#### 2.4.2 Usage Example

```python
from domain.location.snippet import SnippetExtractor
from domain.location.resolver import LocationResolver
from models.location import HeadingLocation
from infra.filesystem import FileSystem

fs = FileSystem()
extractor = SnippetExtractor(fs)

# Extract by heading
location = HeadingLocation(path=["Requirements", "Logging"])
snippet = extractor.extract_snippet("docs/system.md", location)
print(snippet)

# Extract by line range
location = LineLocation(start=10, end=25)
snippet = extractor.extract_snippet("docs/system.md", location)
print(snippet)
```

#### 2.4.3 Testing Guidelines

**Unit Tests**:
- Test extracting snippet by heading path
- Test extracting snippet by line range
- Test extracting from nested headings
- Test extracting when heading is at end of file
- Test error handling for invalid heading path
- Test error handling for invalid line range

**Performance Requirements**:
- Extract snippet: < 100ms for typical file
- CRITICAL: Must meet FR-7.7 requirement (< 100ms)

---

### 2.5 Linking Engine Module

**Location**: `contextgit/domain/linking/engine.py`

**Purpose**: Build and maintain the traceability graph.

**Dependencies**:
- `models.index.Index`
- `models.link.Link`
- `models.node.Node`
- `models.enums.RelationType, SyncStatus`

#### 2.5.1 Public API

```python
class LinkingEngine:
    """Manages traceability links and graph operations."""

    def build_links_from_metadata(
        self,
        nodes: dict[str, Node],
        metadata_map: dict[str, RawMetadata]
    ) -> list[Link]:
        """
        Build links based on upstream/downstream in metadata.

        Infers relation types based on node types.

        Args:
            nodes: All nodes in index
            metadata_map: Metadata for each node

        Returns:
            List of links to add to index
        """

    def update_sync_status(
        self, index: Index, changed_node_ids: set[str]
    ) -> None:
        """
        Update sync status for links affected by changed nodes.

        Sets UPSTREAM_CHANGED or DOWNSTREAM_CHANGED as appropriate.

        Args:
            index: Index to update (modified in place)
            changed_node_ids: Set of node IDs that changed
        """

    def get_upstream_nodes(
        self, index: Index, node_id: str, depth: int = 1
    ) -> list[Node]:
        """
        Get all upstream nodes up to specified depth.

        Uses breadth-first traversal.

        Args:
            index: Index to search
            node_id: Starting node
            depth: How many levels to traverse (default: 1)

        Returns:
            List of upstream nodes
        """

    def get_downstream_nodes(
        self, index: Index, node_id: str, depth: int = 1
    ) -> list[Node]:
        """
        Get all downstream nodes up to specified depth.

        Uses breadth-first traversal.

        Args:
            index: Index to search
            node_id: Starting node
            depth: How many levels to traverse (default: 1)

        Returns:
            List of downstream nodes
        """

    def detect_orphans(
        self, index: Index
    ) -> tuple[list[str], list[str]]:
        """
        Detect orphan nodes (no upstream or no downstream).

        Business nodes don't need upstream.
        Code/test nodes don't need downstream.

        Args:
            index: Index to analyze

        Returns:
            Tuple of (nodes_without_upstream, nodes_without_downstream)
        """
```

#### 2.5.2 Usage Example

```python
from domain.linking.engine import LinkingEngine

engine = LinkingEngine()

# Build links from metadata
links = engine.build_links_from_metadata(nodes, metadata_map)

# Add links to index
for link in links:
    index.links.append(link)

# Update sync status after changes
changed_nodes = {"SR-010", "SR-011"}
engine.update_sync_status(index, changed_nodes)

# Find upstream nodes
upstream = engine.get_upstream_nodes(index, "C-120", depth=3)
for node in upstream:
    print(f"Upstream: {node.id} - {node.title}")

# Detect orphans
no_upstream, no_downstream = engine.detect_orphans(index)
print(f"Orphans without upstream: {no_upstream}")
```

#### 2.5.3 Testing Guidelines

**Unit Tests**:
- Test building links from metadata
- Test relation type inference for all node type combinations
- Test updating sync status when upstream changes
- Test updating sync status when downstream changes
- Test upstream traversal (single level and multi-level)
- Test downstream traversal (single level and multi-level)
- Test orphan detection
- Test circular dependency detection (future)

**Performance Requirements**:
- Build links: O(N) where N = number of nodes
- Update sync status: O(L) where L = number of links
- Traverse graph: O(N) worst case

---

### 2.6 Checksum Calculator Module

**Location**: `contextgit/domain/checksum/calculator.py`

**Purpose**: Calculate and compare content checksums for change detection.

**Dependencies**: None (uses standard library `hashlib`)

#### 2.6.1 Public API

```python
class ChecksumCalculator:
    """Calculates and compares content checksums."""

    def calculate_checksum(self, text: str) -> str:
        """
        Calculate SHA-256 checksum of normalized text.

        Normalization:
        - Convert line endings to \\n
        - Strip whitespace from each line
        - Remove empty lines at start/end

        Args:
            text: Input text

        Returns:
            Hex digest (64 characters)
        """

    def compare_checksums(self, old: str, new: str) -> bool:
        """
        Compare two checksums.

        Args:
            old: First checksum
            new: Second checksum

        Returns:
            True if identical, False otherwise
        """
```

#### 2.6.2 Usage Example

```python
from domain.checksum.calculator import ChecksumCalculator

calc = ChecksumCalculator()

# Calculate checksum
text = "Some requirement text\\nWith multiple lines\\n"
checksum = calc.calculate_checksum(text)
print(f"Checksum: {checksum}")

# Compare checksums
old_checksum = "abc123..."
new_checksum = calc.calculate_checksum(updated_text)

if not calc.compare_checksums(old_checksum, new_checksum):
    print("Content has changed!")
```

#### 2.6.3 Testing Guidelines

**Unit Tests**:
- Test checksum calculation produces 64-character hex string
- Test normalization removes leading/trailing whitespace
- Test normalization handles different line endings
- Test identical text produces identical checksum
- Test whitespace-only changes don't affect checksum

**Performance Requirements**:
- Calculate checksum: < 10ms for typical snippet (< 5KB)

---

### 2.7 ID Generator Module

**Location**: `contextgit/domain/id_gen/generator.py`

**Purpose**: Generate next sequential ID for nodes.

**Dependencies**:
- `models.index.Index`
- `models.config.Config`

#### 2.7.1 Public API

```python
class IDGenerator:
    """Generates next sequential ID for nodes."""

    def next_id(
        self, node_type: str, index: Index, config: Config
    ) -> str:
        """
        Generate next ID for node type.

        Args:
            node_type: Node type (business, system, etc.)
            index: Current index
            config: Configuration with prefixes

        Returns:
            Next ID (e.g., "SR-012")

        Raises:
            ValueError: If node type has no configured prefix
        """
```

#### 2.7.2 Usage Example

```python
from domain.id_gen.generator import IDGenerator

generator = IDGenerator()

# Generate next system requirement ID
next_id = generator.next_id("system", index, config)
print(f"Next ID: {next_id}")  # e.g., "SR-012"
```

#### 2.7.3 Testing Guidelines

**Unit Tests**:
- Test generating first ID (should be 001)
- Test generating next ID after existing IDs
- Test handling gaps in ID sequence
- Test zero-padding (001, 010, 100)
- Test error for unknown node type

**Performance Requirements**:
- Generate ID: < 10ms (O(N) scan of existing IDs)

---

### 2.8 Config Manager Module

**Location**: `contextgit/domain/config/manager.py`

**Purpose**: Load and manage configuration.

**Dependencies**:
- `models.config.Config`
- `infra.filesystem.FileSystem`
- `infra.yaml_io.YAMLSerializer`

#### 2.8.1 Public API

```python
class ConfigManager:
    """Manages configuration loading and saving."""

    def __init__(
        self,
        filesystem: FileSystem,
        yaml_io: YAMLSerializer,
        repo_root: str
    ):
        """
        Initialize ConfigManager.

        Args:
            filesystem: File system abstraction
            yaml_io: YAML serialization handler
            repo_root: Repository root path
        """

    def load_config(self) -> Config:
        """
        Load configuration from .contextgit/config.yaml.

        Returns default config if file doesn't exist.

        Returns:
            Config object

        Raises:
            InvalidConfigError: If config file is malformed
        """

    def save_config(self, config: Config) -> None:
        """
        Save configuration to .contextgit/config.yaml.

        Args:
            config: Config to save
        """

    @staticmethod
    def get_default_config() -> Config:
        """
        Get default configuration.

        Returns:
            Config with default values
        """
```

#### 2.8.2 Usage Example

```python
from domain.config.manager import ConfigManager

manager = ConfigManager(fs, yaml, repo_root)

# Load config
config = manager.load_config()
print(f"System prefix: {config.tag_prefixes['system']}")

# Modify and save
config.tag_prefixes['custom'] = "CUS-"
manager.save_config(config)
```

---

## 3. Infrastructure Layer Modules

### 3.1 File System Module

**Location**: `contextgit/infra/filesystem.py`

**Purpose**: Abstract file system operations for testability.

**Dependencies**: None (uses standard library `os`, `pathlib`)

#### 3.1.1 Public API

```python
class FileSystem:
    """File system operations abstraction."""

    def read_file(self, path: str) -> str:
        """
        Read file as UTF-8 text.

        Args:
            path: File path

        Returns:
            File contents

        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If file is not valid UTF-8
        """

    def write_file_atomic(self, path: str, content: str) -> None:
        """
        Write file atomically using temp file + rename.

        Ensures file is never corrupted even if process crashes.

        Args:
            path: File path
            content: Content to write

        Raises:
            IOError: If write fails
        """

    def walk_files(
        self, root: str, pattern: str = "*.md", recursive: bool = False
    ) -> Iterator[str]:
        """
        Walk directory tree and yield matching files.

        Args:
            root: Root directory (or single file path)
            pattern: Glob pattern (default: "*.md")
            recursive: Whether to recurse subdirectories

        Yields:
            File paths
        """

    def find_repo_root(self, start_path: str) -> str:
        """
        Find repository root by looking for .contextgit/ or .git/.

        Args:
            start_path: Starting path (file or directory)

        Returns:
            Repository root path

        Raises:
            FileNotFoundError: If not in a repository
        """
```

#### 3.1.2 Testing Guidelines

**Unit Tests**:
- Test reading existing file
- Test reading non-existent file (should raise)
- Test atomic write (verify temp file is used)
- Test atomic write cleanup on error
- Test walk_files with single file
- Test walk_files with directory (recursive and non-recursive)
- Test find_repo_root from various subdirectories
- Test find_repo_root error when not in repo

---

### 3.2 YAML Serialization Module

**Location**: `contextgit/infra/yaml_io.py`

**Purpose**: Provide deterministic YAML serialization for git-friendliness.

**Dependencies**: `ruamel.yaml`

#### 3.2.1 Public API

```python
class YAMLSerializer:
    """YAML serialization with deterministic output."""

    def __init__(self):
        """Initialize with ruamel.yaml configuration for deterministic output."""

    def load_yaml(self, content: str) -> dict:
        """
        Parse YAML safely.

        Args:
            content: YAML string

        Returns:
            Parsed dictionary

        Raises:
            yaml.YAMLError: If YAML is malformed
        """

    def dump_yaml(self, data: dict) -> str:
        """
        Dump YAML with deterministic formatting.

        - 2-space indentation
        - Sorted keys
        - Block style

        Args:
            data: Dictionary to serialize

        Returns:
            YAML string
        """
```

#### 3.2.2 Testing Guidelines

**Unit Tests**:
- Test loading valid YAML
- Test loading invalid YAML (should raise)
- Test dumping produces deterministic output
- Test multiple dumps of same data produce identical strings
- Test sorted keys
- Test proper indentation

---

### 3.3 Output Formatter Module

**Location**: `contextgit/infra/output.py`

**Purpose**: Format output as human-readable text or JSON.

**Dependencies**:
- `rich` (for terminal formatting)
- `json` (standard library)

#### 3.3.1 Public API

```python
class OutputFormatter:
    """Format output as text or JSON."""

    def format_status(
        self, index: Index, format: str
    ) -> str:
        """
        Format status command output.

        Args:
            index: Index to format
            format: "text" or "json"

        Returns:
            Formatted output
        """

    def format_node(
        self, node: Node, format: str
    ) -> str:
        """
        Format node details.

        Args:
            node: Node to format
            format: "text" or "json"

        Returns:
            Formatted output
        """

    def format_extract_result(
        self,
        node: Node,
        snippet: str,
        format: str
    ) -> str:
        """
        Format extract command result.

        Args:
            node: Node metadata
            snippet: Extracted text
            format: "text" or "json"

        Returns:
            Formatted output
        """

    def format_scan_result(
        self, summary: dict, format: str
    ) -> str:
        """
        Format scan command result.

        Args:
            summary: Scan summary data
            format: "text" or "json"

        Returns:
            Formatted output
        """
```

---

## 4. Handler Layer Modules

### 4.1 Base Handler

**Location**: `contextgit/handlers/base.py`

**Purpose**: Provide common functionality for all handlers.

#### 4.1.1 Public API

```python
class BaseHandler:
    """Base class for command handlers."""

    def __init__(
        self,
        filesystem: FileSystem,
        yaml_io: YAMLSerializer,
        output_formatter: OutputFormatter,
    ):
        """
        Initialize base handler.

        Args:
            filesystem: File system abstraction
            yaml_io: YAML serialization
            output_formatter: Output formatting
        """

    def find_repo_root(self, start_path: str | None = None) -> str:
        """
        Find repository root.

        Args:
            start_path: Starting path (default: current directory)

        Returns:
            Repository root path

        Raises:
            RepoNotFoundError: If not in a repository
        """
```

---

### 4.2 Handler Modules

Each handler follows this pattern:

**Location**: `contextgit/handlers/{command}_handler.py`

**Class Name**: `{Command}Handler`

**Method**: `handle(...) -> str`

**Example**:
```python
class ScanHandler(BaseHandler):
    def handle(
        self,
        path: str,
        recursive: bool,
        dry_run: bool,
        format: str,
    ) -> str:
        """
        Execute scan command.

        Args:
            path: Path to scan
            recursive: Scan recursively
            dry_run: Don't modify index
            format: Output format

        Returns:
            Formatted output
        """
```

---

## 5. Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  (depends on handlers only)                                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     Handler Layer                            │
│  (depends on domain + infra)                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                  │
┌────────▼────────┐              ┌─────────▼─────────┐
│  Domain Layer   │              │  Infra Layer      │
│  (depends on    │              │  (no dependencies,│
│   infra only)   │              │   uses stdlib)    │
└─────────────────┘              └───────────────────┘
```

**Key Principles**:
1. Domain layer depends on infra layer only
2. Handlers depend on both domain and infra
3. CLI depends on handlers only
4. Models are shared across all layers
5. No circular dependencies

---

## 6. Summary

This module specification provides:

1. **Complete API documentation** for all public interfaces
2. **Usage examples** for each module
3. **Testing guidelines** with specific test cases
4. **Performance requirements** linked to system requirements
5. **Clear dependency graph** ensuring no circular dependencies

All modules are ready for implementation with well-defined interfaces and responsibilities.
