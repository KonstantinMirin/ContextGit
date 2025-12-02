# Detailed Software Design Document

## 1. Introduction

### 1.1 Purpose
This document provides detailed class designs, algorithms, and implementation specifications for all modules in the contextgit system. It builds upon the architecture in `01_software_architecture.md` with concrete implementation details.

### 1.2 Conventions
- All code examples are in Python 3.11+
- Type hints are mandatory for all public interfaces
- Dataclasses are used for data structures
- `|` notation for union types (e.g., `str | None`)

---

## 2. Data Models

### 2.1 Core Data Classes

#### 2.1.1 Node

```python
from dataclasses import dataclass, field
from datetime import datetime
from models.enums import NodeType, NodeStatus
from models.location import Location

@dataclass
class Node:
    """Represents a requirement or context item in the system."""

    id: str
    type: NodeType
    title: str
    file: str  # Relative path from repo root
    location: Location
    status: NodeStatus
    last_updated: str  # ISO 8601 timestamp
    checksum: str  # SHA-256 hex digest
    llm_generated: bool = False
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate node data."""
        if not self.id or not self.id.strip():
            raise ValueError("Node ID cannot be empty")
        if not self.title or not self.title.strip():
            raise ValueError("Node title cannot be empty")
        if len(self.checksum) != 64:
            raise ValueError(f"Invalid checksum length: {len(self.checksum)}")

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            'id': self.id,
            'type': self.type.value,
            'title': self.title,
            'file': self.file,
            'location': self.location.to_dict(),
            'status': self.status.value,
            'last_updated': self.last_updated,
            'checksum': self.checksum,
            'llm_generated': self.llm_generated,
            'tags': sorted(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Node':
        """Create Node from dictionary (YAML deserialization)."""
        return cls(
            id=data['id'],
            type=NodeType(data['type']),
            title=data['title'],
            file=data['file'],
            location=Location.from_dict(data['location']),
            status=NodeStatus(data.get('status', 'active')),
            last_updated=data['last_updated'],
            checksum=data['checksum'],
            llm_generated=data.get('llm_generated', False),
            tags=data.get('tags', []),
        )
```

---

#### 2.1.2 Link

```python
from dataclasses import dataclass
from models.enums import RelationType, SyncStatus

@dataclass
class Link:
    """Represents a traceability relationship between two nodes."""

    from_id: str  # Source node ID (upstream)
    to_id: str    # Target node ID (downstream)
    relation_type: RelationType
    sync_status: SyncStatus
    last_checked: str  # ISO 8601 timestamp

    def __post_init__(self):
        """Validate link data."""
        if not self.from_id or not self.to_id:
            raise ValueError("Link IDs cannot be empty")
        if self.from_id == self.to_id:
            raise ValueError("Self-referential link not allowed")

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            'from': self.from_id,
            'to': self.to_id,
            'relation_type': self.relation_type.value,
            'sync_status': self.sync_status.value,
            'last_checked': self.last_checked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Link':
        """Create Link from dictionary (YAML deserialization)."""
        return cls(
            from_id=data['from'],
            to_id=data['to'],
            relation_type=RelationType(data['relation_type']),
            sync_status=SyncStatus(data['sync_status']),
            last_checked=data['last_checked'],
        )
```

---

#### 2.1.3 Location Types

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class HeadingLocation:
    """Location identified by heading path."""
    kind: Literal["heading"] = "heading"
    path: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {'kind': 'heading', 'path': self.path}

    @classmethod
    def from_dict(cls, data: dict) -> 'HeadingLocation':
        return cls(path=data['path'])


@dataclass
class LineLocation:
    """Location identified by line range."""
    kind: Literal["lines"] = "lines"
    start: int = 1
    end: int = 1

    def __post_init__(self):
        if self.start < 1 or self.end < 1:
            raise ValueError("Line numbers must be >= 1")
        if self.start > self.end:
            raise ValueError(f"Invalid range: {self.start}-{self.end}")

    def to_dict(self) -> dict:
        return {'kind': 'lines', 'start': self.start, 'end': self.end}

    @classmethod
    def from_dict(cls, data: dict) -> 'LineLocation':
        return cls(start=data['start'], end=data['end'])


# Union type for all location types
Location = HeadingLocation | LineLocation


# Factory function for creating Location from dict
def location_from_dict(data: dict) -> Location:
    if data['kind'] == 'heading':
        return HeadingLocation.from_dict(data)
    elif data['kind'] == 'lines':
        return LineLocation.from_dict(data)
    else:
        raise ValueError(f"Unknown location kind: {data['kind']}")
```

---

#### 2.1.4 Index

```python
from dataclasses import dataclass, field

@dataclass
class Index:
    """Container for all nodes and links in the system."""

    nodes: dict[str, Node] = field(default_factory=dict)
    links: list[Link] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            'nodes': [node.to_dict() for node in sorted(
                self.nodes.values(), key=lambda n: n.id
            )],
            'links': [link.to_dict() for link in sorted(
                self.links, key=lambda l: (l.from_id, l.to_id)
            )],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Index':
        """Create Index from dictionary (YAML deserialization)."""
        nodes = {
            node_data['id']: Node.from_dict(node_data)
            for node_data in data.get('nodes', [])
        }
        links = [Link.from_dict(link_data) for link_data in data.get('links', [])]
        return cls(nodes=nodes, links=links)
```

---

#### 2.1.5 Config

```python
from dataclasses import dataclass, field

@dataclass
class Config:
    """Configuration for contextgit project."""

    tag_prefixes: dict[str, str] = field(default_factory=dict)
    directories: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            'tag_prefixes': dict(sorted(self.tag_prefixes.items())),
            'directories': dict(sorted(self.directories.items())),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """Create Config from dictionary (YAML deserialization)."""
        return cls(
            tag_prefixes=data.get('tag_prefixes', {}),
            directories=data.get('directories', {}),
        )

    @classmethod
    def get_default(cls) -> 'Config':
        """Get default configuration."""
        return cls(
            tag_prefixes={
                'business': 'BR-',
                'system': 'SR-',
                'architecture': 'AR-',
                'code': 'C-',
                'test': 'T-',
                'decision': 'ADR-',
            },
            directories={
                'business': 'docs/01_business',
                'system': 'docs/02_system',
                'architecture': 'docs/03_architecture',
                'code': 'src',
                'test': 'tests',
            },
        )
```

---

#### 2.1.6 Enums

```python
from enum import Enum

class NodeType(Enum):
    """Node type enumeration."""
    BUSINESS = "business"
    SYSTEM = "system"
    ARCHITECTURE = "architecture"
    CODE = "code"
    TEST = "test"
    DECISION = "decision"
    OTHER = "other"


class NodeStatus(Enum):
    """Node status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class RelationType(Enum):
    """Relation type enumeration."""
    REFINES = "refines"
    IMPLEMENTS = "implements"
    TESTS = "tests"
    DERIVED_FROM = "derived_from"
    DEPENDS_ON = "depends_on"


class SyncStatus(Enum):
    """Sync status enumeration."""
    OK = "ok"
    UPSTREAM_CHANGED = "upstream_changed"
    DOWNSTREAM_CHANGED = "downstream_changed"
    BROKEN = "broken"
```

---

## 3. Domain Layer Detailed Design

### 3.1 Index Manager

#### 3.1.1 Class Definition

```python
from pathlib import Path
from models.index import Index
from models.node import Node
from models.link import Link
from infra.filesystem import FileSystem
from infra.yaml_io import YAMLSerializer
from exceptions import IndexCorruptedError, NodeNotFoundError

class IndexManager:
    """Manages CRUD operations for the requirements index."""

    INDEX_FILE = ".contextgit/requirements_index.yaml"

    def __init__(self, filesystem: FileSystem, yaml_io: YAMLSerializer, repo_root: str):
        self.fs = filesystem
        self.yaml = yaml_io
        self.repo_root = Path(repo_root)
        self.index_path = self.repo_root / self.INDEX_FILE
        self._index: Index | None = None

    def load_index(self) -> Index:
        """Load index from disk. Cache in memory."""
        if self._index is not None:
            return self._index

        if not self.index_path.exists():
            # Return empty index if file doesn't exist
            self._index = Index()
            return self._index

        try:
            content = self.fs.read_file(str(self.index_path))
            data = self.yaml.load_yaml(content)
            self._index = Index.from_dict(data)
            return self._index
        except Exception as e:
            raise IndexCorruptedError(f"Failed to load index: {e}")

    def save_index(self, index: Index) -> None:
        """Save index to disk atomically."""
        # Validate before saving
        self._validate_index(index)

        # Convert to dict and serialize
        data = index.to_dict()
        content = self.yaml.dump_yaml(data)

        # Write atomically
        self.fs.write_file_atomic(str(self.index_path), content)

        # Update cache
        self._index = index

    def get_node(self, node_id: str) -> Node:
        """Get node by ID. Raises NodeNotFoundError if not found."""
        index = self.load_index()
        if node_id not in index.nodes:
            raise NodeNotFoundError(f"Node not found: {node_id}")
        return index.nodes[node_id]

    def add_node(self, node: Node) -> None:
        """Add a new node to the index."""
        index = self.load_index()
        if node.id in index.nodes:
            raise ValueError(f"Node {node.id} already exists")
        index.nodes[node.id] = node

    def update_node(self, node_id: str, updates: dict) -> None:
        """Update an existing node."""
        index = self.load_index()
        if node_id not in index.nodes:
            raise NodeNotFoundError(f"Node not found: {node_id}")

        node = index.nodes[node_id]
        # Create updated node (dataclasses are immutable-ish)
        updated_node = dataclasses.replace(node, **updates)
        index.nodes[node_id] = updated_node

    def delete_node(self, node_id: str) -> None:
        """Delete a node from the index."""
        index = self.load_index()
        if node_id not in index.nodes:
            raise NodeNotFoundError(f"Node not found: {node_id}")
        del index.nodes[node_id]

    def add_link(self, link: Link) -> None:
        """Add a new link to the index."""
        index = self.load_index()

        # Validate that both nodes exist
        if link.from_id not in index.nodes:
            raise NodeNotFoundError(f"Source node not found: {link.from_id}")
        if link.to_id not in index.nodes:
            raise NodeNotFoundError(f"Target node not found: {link.to_id}")

        # Check if link already exists
        existing = self.get_link(link.from_id, link.to_id)
        if existing:
            raise ValueError(f"Link already exists: {link.from_id} -> {link.to_id}")

        index.links.append(link)

    def update_link(self, from_id: str, to_id: str, updates: dict) -> None:
        """Update an existing link."""
        index = self.load_index()
        link = self.get_link(from_id, to_id)
        if not link:
            raise ValueError(f"Link not found: {from_id} -> {to_id}")

        # Find and update
        for i, l in enumerate(index.links):
            if l.from_id == from_id and l.to_id == to_id:
                updated_link = dataclasses.replace(l, **updates)
                index.links[i] = updated_link
                break

    def get_link(self, from_id: str, to_id: str) -> Link | None:
        """Get a specific link, or None if not found."""
        index = self.load_index()
        for link in index.links:
            if link.from_id == from_id and link.to_id == to_id:
                return link
        return None

    def get_links_from(self, node_id: str) -> list[Link]:
        """Get all outgoing links from a node."""
        index = self.load_index()
        return [link for link in index.links if link.from_id == node_id]

    def get_links_to(self, node_id: str) -> list[Link]:
        """Get all incoming links to a node."""
        index = self.load_index()
        return [link for link in index.links if link.to_id == node_id]

    def _validate_index(self, index: Index) -> None:
        """Validate index structure before saving."""
        # Check for duplicate node IDs (should not happen with dict)
        node_ids = set()
        for node_id in index.nodes:
            if node_id in node_ids:
                raise ValueError(f"Duplicate node ID: {node_id}")
            node_ids.add(node_id)

        # Check that all links reference existing nodes
        for link in index.links:
            if link.from_id not in index.nodes:
                raise ValueError(f"Link references non-existent node: {link.from_id}")
            if link.to_id not in index.nodes:
                raise ValueError(f"Link references non-existent node: {link.to_id}")
```

---

### 3.2 Metadata Parser

#### 3.2.1 Class Definition

```python
import re
from pathlib import Path
from dataclasses import dataclass
from infra.filesystem import FileSystem
from exceptions import InvalidMetadataError

@dataclass
class RawMetadata:
    """Raw metadata extracted from file before validation."""
    id: str
    type: str
    title: str
    upstream: list[str]
    downstream: list[str]
    status: str = "active"
    tags: list[str] = None
    llm_generated: bool = False
    line_number: int = 0  # Line where metadata block starts

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MetadataParser:
    """Parses contextgit metadata from Markdown files."""

    def __init__(self, filesystem: FileSystem):
        self.fs = filesystem

    def parse_file(self, file_path: str) -> list[RawMetadata]:
        """Parse all metadata blocks in a file."""
        content = self.fs.read_file(file_path)

        metadata_blocks = []

        # Try frontmatter first
        frontmatter = self._parse_frontmatter(content)
        if frontmatter:
            metadata_blocks.append(frontmatter)

        # Parse inline blocks
        inline_blocks = self._parse_inline_blocks(content)
        metadata_blocks.extend(inline_blocks)

        return metadata_blocks

    def _parse_frontmatter(self, content: str) -> RawMetadata | None:
        """Parse YAML frontmatter at the beginning of file."""
        # Check if file starts with ---
        if not content.startswith('---'):
            return None

        # Find closing ---
        lines = content.split('\n')
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_idx = i
                break

        if end_idx is None:
            return None

        # Extract YAML content
        yaml_content = '\n'.join(lines[1:end_idx])

        # Parse YAML
        try:
            from infra.yaml_io import YAMLSerializer
            yaml = YAMLSerializer()
            data = yaml.load_yaml(yaml_content)

            # Check for 'contextgit' key
            if 'contextgit' not in data:
                return None

            cg_data = data['contextgit']
            return self._extract_metadata(cg_data, line_number=1)

        except Exception as e:
            raise InvalidMetadataError(f"Invalid frontmatter: {e}")

    def _parse_inline_blocks(self, content: str) -> list[RawMetadata]:
        """Parse inline HTML comment blocks."""
        blocks = []

        # Regex to find <!-- contextgit ... -->
        pattern = r'<!--\s*contextgit\s*\n(.*?)\n\s*-->'
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            yaml_content = match.group(1)
            line_number = content[:match.start()].count('\n') + 1

            try:
                from infra.yaml_io import YAMLSerializer
                yaml = YAMLSerializer()
                data = yaml.load_yaml(yaml_content)
                metadata = self._extract_metadata(data, line_number)
                blocks.append(metadata)
            except Exception as e:
                raise InvalidMetadataError(
                    f"Invalid inline block at line {line_number}: {e}"
                )

        return blocks

    def _extract_metadata(self, data: dict, line_number: int) -> RawMetadata:
        """Extract and validate metadata from parsed YAML."""
        # Required fields
        if 'id' not in data:
            raise InvalidMetadataError(f"Missing 'id' field at line {line_number}")
        if 'type' not in data:
            raise InvalidMetadataError(f"Missing 'type' field at line {line_number}")
        if 'title' not in data:
            raise InvalidMetadataError(f"Missing 'title' field at line {line_number}")

        return RawMetadata(
            id=data['id'],
            type=data['type'],
            title=data['title'],
            upstream=data.get('upstream', []),
            downstream=data.get('downstream', []),
            status=data.get('status', 'active'),
            tags=data.get('tags', []),
            llm_generated=data.get('llm_generated', False),
            line_number=line_number,
        )
```

---

### 3.3 Location Resolver & Snippet Extractor

#### 3.3.1 Markdown Structure Parser

```python
from dataclasses import dataclass

@dataclass
class Heading:
    """Represents a Markdown heading."""
    level: int  # 1-6 (# = 1, ## = 2, etc.)
    text: str
    line_number: int


class MarkdownParser:
    """Parses Markdown structure to identify headings."""

    def parse_headings(self, content: str) -> list[Heading]:
        """Parse all headings in Markdown content."""
        headings = []
        lines = content.split('\n')

        for i, line in enumerate(lines, start=1):
            # Check for ATX-style headings (# Heading)
            if line.startswith('#'):
                # Count leading #
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break

                if level > 0 and level <= 6:
                    text = line[level:].strip()
                    headings.append(Heading(level=level, text=text, line_number=i))

        return headings
```

---

#### 3.3.2 Location Resolver

```python
from models.location import HeadingLocation, LineLocation, Location

class LocationResolver:
    """Resolves metadata block locations in Markdown files."""

    def __init__(self, filesystem: FileSystem):
        self.fs = filesystem
        self.md_parser = MarkdownParser()

    def resolve_location(self, file_path: str, metadata_line: int) -> Location:
        """
        Resolve location for a metadata block.

        Args:
            file_path: Path to the Markdown file
            metadata_line: Line number where metadata block starts

        Returns:
            Location object (heading or line-based)
        """
        content = self.fs.read_file(file_path)
        headings = self.md_parser.parse_headings(content)

        # Find the heading immediately after the metadata block
        next_heading = None
        for heading in headings:
            if heading.line_number > metadata_line:
                next_heading = heading
                break

        if next_heading is None:
            # No heading after metadata, use line-based location
            lines = content.split('\n')
            return LineLocation(start=metadata_line, end=len(lines))

        # Build heading path
        path = self._build_heading_path(headings, next_heading)
        return HeadingLocation(path=path)

    def _build_heading_path(self, all_headings: list[Heading], target: Heading) -> list[str]:
        """Build the full heading path for a target heading."""
        path = []
        current_level = target.level

        # Add target heading
        path.append(target.text)

        # Walk backwards to find parent headings
        for heading in reversed(all_headings):
            if heading.line_number >= target.line_number:
                continue

            if heading.level < current_level:
                path.insert(0, heading.text)
                current_level = heading.level

            if current_level == 1:
                break

        return path
```

---

#### 3.3.3 Snippet Extractor

```python
class SnippetExtractor:
    """Extracts text snippets from files based on locations."""

    def __init__(self, filesystem: FileSystem):
        self.fs = filesystem
        self.md_parser = MarkdownParser()

    def extract_snippet(self, file_path: str, location: Location) -> str:
        """Extract text snippet from file based on location."""
        content = self.fs.read_file(file_path)

        if isinstance(location, LineLocation):
            return self._extract_by_lines(content, location)
        elif isinstance(location, HeadingLocation):
            return self._extract_by_heading(content, location)
        else:
            raise ValueError(f"Unknown location type: {type(location)}")

    def _extract_by_lines(self, content: str, location: LineLocation) -> str:
        """Extract snippet by line range."""
        lines = content.split('\n')
        # Line numbers are 1-indexed
        start_idx = location.start - 1
        end_idx = location.end
        return '\n'.join(lines[start_idx:end_idx])

    def _extract_by_heading(self, content: str, location: HeadingLocation) -> str:
        """Extract snippet by heading path."""
        headings = self.md_parser.parse_headings(content)

        # Find the target heading
        target_heading = self._find_heading_by_path(headings, location.path)
        if not target_heading:
            raise ValueError(f"Heading not found: {location.path}")

        # Find the next same-level or higher-level heading
        end_line = None
        for heading in headings:
            if heading.line_number > target_heading.line_number:
                if heading.level <= target_heading.level:
                    end_line = heading.line_number - 1
                    break

        # Extract from target heading to end
        lines = content.split('\n')
        start_idx = target_heading.line_number - 1

        if end_line:
            end_idx = end_line
        else:
            end_idx = len(lines)

        return '\n'.join(lines[start_idx:end_idx])

    def _find_heading_by_path(
        self, headings: list[Heading], path: list[str]
    ) -> Heading | None:
        """Find a heading by its full path."""
        if not path:
            return None

        # Build heading paths for all headings
        for i, heading in enumerate(headings):
            heading_path = self._build_path_for_heading(headings[:i+1], heading)
            if heading_path == path:
                return heading

        return None

    def _build_path_for_heading(
        self, preceding_headings: list[Heading], target: Heading
    ) -> list[str]:
        """Build path for a heading based on preceding headings."""
        path = []
        current_level = target.level

        # Add target
        path.append(target.text)

        # Walk backwards
        for heading in reversed(preceding_headings[:-1]):
            if heading.level < current_level:
                path.insert(0, heading.text)
                current_level = heading.level

        return path
```

---

### 3.4 Linking Engine

```python
from datetime import datetime, timezone
from models.index import Index
from models.link import Link
from models.enums import RelationType, SyncStatus

class LinkingEngine:
    """Manages traceability links and graph operations."""

    def build_links_from_metadata(
        self,
        nodes: dict[str, Node],
        metadata_map: dict[str, RawMetadata]
    ) -> list[Link]:
        """Build links based on upstream/downstream in metadata."""
        links = []
        now = datetime.now(timezone.utc).isoformat()

        for node_id, metadata in metadata_map.items():
            # Create links from upstream
            for upstream_id in metadata.upstream:
                if upstream_id in nodes:
                    relation = self._infer_relation_type(
                        nodes[upstream_id].type,
                        nodes[node_id].type
                    )
                    links.append(Link(
                        from_id=upstream_id,
                        to_id=node_id,
                        relation_type=relation,
                        sync_status=SyncStatus.OK,
                        last_checked=now,
                    ))

            # Create links from downstream
            for downstream_id in metadata.downstream:
                if downstream_id in nodes:
                    relation = self._infer_relation_type(
                        nodes[node_id].type,
                        nodes[downstream_id].type
                    )
                    links.append(Link(
                        from_id=node_id,
                        to_id=downstream_id,
                        relation_type=relation,
                        sync_status=SyncStatus.OK,
                        last_checked=now,
                    ))

        return links

    def _infer_relation_type(
        self, from_type: NodeType, to_type: NodeType
    ) -> RelationType:
        """Infer relation type based on node types."""
        # business -> system: refines
        # system -> architecture: refines
        # architecture -> code: implements
        # code -> test: tests

        if to_type == NodeType.TEST:
            return RelationType.TESTS

        if from_type == NodeType.BUSINESS:
            return RelationType.REFINES

        if from_type == NodeType.SYSTEM:
            if to_type == NodeType.CODE:
                return RelationType.IMPLEMENTS
            return RelationType.REFINES

        if from_type == NodeType.ARCHITECTURE:
            return RelationType.IMPLEMENTS

        # Default
        return RelationType.REFINES

    def update_sync_status(
        self, index: Index, changed_node_ids: set[str]
    ) -> None:
        """Update sync status for links affected by changed nodes."""
        now = datetime.now(timezone.utc).isoformat()

        for link in index.links:
            # If upstream node changed
            if link.from_id in changed_node_ids:
                link.sync_status = SyncStatus.UPSTREAM_CHANGED
                link.last_checked = now

            # If downstream node changed
            if link.to_id in changed_node_ids:
                link.sync_status = SyncStatus.DOWNSTREAM_CHANGED
                link.last_checked = now

    def get_upstream_nodes(
        self, index: Index, node_id: str, depth: int = 1
    ) -> list[Node]:
        """Get all upstream nodes up to specified depth."""
        visited = set()
        result = []

        def traverse(current_id: str, current_depth: int):
            if current_depth > depth or current_id in visited:
                return

            visited.add(current_id)

            # Find incoming links
            for link in index.links:
                if link.to_id == current_id and link.from_id not in visited:
                    upstream_node = index.nodes.get(link.from_id)
                    if upstream_node:
                        result.append(upstream_node)
                        traverse(link.from_id, current_depth + 1)

        traverse(node_id, 0)
        return result

    def get_downstream_nodes(
        self, index: Index, node_id: str, depth: int = 1
    ) -> list[Node]:
        """Get all downstream nodes up to specified depth."""
        visited = set()
        result = []

        def traverse(current_id: str, current_depth: int):
            if current_depth > depth or current_id in visited:
                return

            visited.add(current_id)

            # Find outgoing links
            for link in index.links:
                if link.from_id == current_id and link.to_id not in visited:
                    downstream_node = index.nodes.get(link.to_id)
                    if downstream_node:
                        result.append(downstream_node)
                        traverse(link.to_id, current_depth + 1)

        traverse(node_id, 0)
        return result

    def detect_orphans(self, index: Index) -> tuple[list[str], list[str]]:
        """
        Detect orphan nodes.

        Returns:
            (nodes_without_upstream, nodes_without_downstream)
        """
        no_upstream = []
        no_downstream = []

        # Build sets of nodes with links
        has_upstream = set()
        has_downstream = set()

        for link in index.links:
            has_downstream.add(link.from_id)
            has_upstream.add(link.to_id)

        # Check each node
        for node_id, node in index.nodes.items():
            # Business requirements don't need upstream
            if node.type != NodeType.BUSINESS and node_id not in has_upstream:
                no_upstream.append(node_id)

            # Code and test don't need downstream
            if node.type not in (NodeType.CODE, NodeType.TEST) and node_id not in has_downstream:
                no_downstream.append(node_id)

        return no_upstream, no_downstream
```

---

### 3.5 Checksum Calculator

```python
import hashlib

class ChecksumCalculator:
    """Calculates and compares content checksums."""

    def calculate_checksum(self, text: str) -> str:
        """
        Calculate SHA-256 checksum of normalized text.

        Args:
            text: Input text

        Returns:
            Hex digest (64 characters)
        """
        normalized = self._normalize_text(text)
        hash_obj = hashlib.sha256(normalized.encode('utf-8'))
        return hash_obj.hexdigest()

    def compare_checksums(self, old: str, new: str) -> bool:
        """Compare two checksums. Returns True if identical."""
        return old == new

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent checksumming.

        - Convert line endings to \\n
        - Strip leading/trailing whitespace from each line
        - Remove empty lines at start/end
        """
        # Convert line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Strip each line
        lines = text.split('\n')
        stripped_lines = [line.strip() for line in lines]

        # Remove empty lines at start/end
        while stripped_lines and not stripped_lines[0]:
            stripped_lines.pop(0)
        while stripped_lines and not stripped_lines[-1]:
            stripped_lines.pop()

        return '\n'.join(stripped_lines)
```

---

### 3.6 ID Generator

```python
import re

class IDGenerator:
    """Generates next sequential ID for nodes."""

    def next_id(self, node_type: str, index: Index, config: Config) -> str:
        """
        Generate next ID for node type.

        Args:
            node_type: Node type (business, system, etc.)
            index: Current index
            config: Configuration with prefixes

        Returns:
            Next ID (e.g., "SR-012")
        """
        # Get prefix from config
        prefix = config.tag_prefixes.get(node_type)
        if not prefix:
            raise ValueError(f"No prefix configured for type: {node_type}")

        # Find all IDs with this prefix
        matching_ids = [
            node_id for node_id in index.nodes.keys()
            if node_id.startswith(prefix)
        ]

        # Extract numeric portions
        max_num = 0
        pattern = re.compile(rf'^{re.escape(prefix)}(\d+)$')

        for node_id in matching_ids:
            match = pattern.match(node_id)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)

        # Generate next ID
        next_num = max_num + 1
        return f"{prefix}{next_num:03d}"
```

---

## 4. Infrastructure Layer Detailed Design

### 4.1 File System

```python
import os
import shutil
from pathlib import Path
from typing import Iterator

class FileSystem:
    """File system operations abstraction."""

    def read_file(self, path: str) -> str:
        """Read file as UTF-8 text."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_file_atomic(self, path: str, content: str) -> None:
        """Write file atomically using temp file + rename."""
        temp_path = path + '.tmp'

        try:
            # Write to temp file
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Atomic rename (POSIX)
            os.rename(temp_path, path)

        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def walk_files(
        self, root: str, pattern: str = "*.md", recursive: bool = False
    ) -> Iterator[str]:
        """Walk directory tree and yield matching files."""
        root_path = Path(root)

        if root_path.is_file():
            yield str(root_path)
            return

        if recursive:
            for file_path in root_path.rglob(pattern):
                if file_path.is_file():
                    yield str(file_path)
        else:
            for file_path in root_path.glob(pattern):
                if file_path.is_file():
                    yield str(file_path)

    def find_repo_root(self, start_path: str) -> str:
        """Find repository root by looking for .contextgit/ or .git/."""
        current = Path(start_path).resolve()

        while current != current.parent:
            if (current / '.contextgit').exists():
                return str(current)
            if (current / '.git').exists():
                return str(current)
            current = current.parent

        raise FileNotFoundError("Not in a contextgit repository")
```

---

### 4.2 YAML Serialization

```python
from ruamel.yaml import YAML

class YAMLSerializer:
    """YAML serialization with deterministic output."""

    def __init__(self):
        self.yaml = YAML()
        self.yaml.default_flow_style = False
        self.yaml.indent(mapping=2, sequence=2, offset=0)
        self.yaml.width = 120
        self.yaml.preserve_quotes = True

    def load_yaml(self, content: str) -> dict:
        """Parse YAML safely."""
        return self.yaml.load(content)

    def dump_yaml(self, data: dict) -> str:
        """Dump YAML with deterministic formatting."""
        from io import StringIO
        stream = StringIO()
        self.yaml.dump(data, stream)
        return stream.getvalue()
```

---

### 4.3 Output Formatter

```python
import json
from rich.console import Console
from rich.table import Table
from models.index import Index
from models.node import Node

class OutputFormatter:
    """Format output as text or JSON."""

    def __init__(self):
        self.console = Console()

    def format_status(self, index: Index, format: str) -> str:
        """Format status command output."""
        if format == 'json':
            return self._format_status_json(index)
        else:
            return self._format_status_text(index)

    def _format_status_text(self, index: Index) -> str:
        """Format status as human-readable text."""
        # Count nodes by type
        type_counts = {}
        for node in index.nodes.values():
            type_name = node.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Count links by status
        total_links = len(index.links)
        stale_links = sum(
            1 for link in index.links
            if link.sync_status != SyncStatus.OK
        )

        lines = []
        lines.append("contextgit status:\\n")
        lines.append("Nodes:")
        for type_name, count in sorted(type_counts.items()):
            lines.append(f"  {type_name}: {count}")

        lines.append(f"\\nLinks: {total_links}")
        lines.append(f"\\nHealth:")
        lines.append(f"  Stale links: {stale_links}")

        return '\\n'.join(lines)

    def _format_status_json(self, index: Index) -> str:
        """Format status as JSON."""
        # Count nodes by type
        type_counts = {}
        for node in index.nodes.values():
            type_name = node.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Count links by status
        stale_links = sum(
            1 for link in index.links
            if link.sync_status != SyncStatus.OK
        )

        data = {
            'nodes': type_counts,
            'links': {
                'total': len(index.links),
                'stale': stale_links,
            },
        }

        return json.dumps(data, indent=2)
```

---

## 5. Handler Implementation Example

### 5.1 Scan Handler

```python
from datetime import datetime, timezone
from pathlib import Path

class ScanHandler:
    """Handler for contextgit scan command."""

    def __init__(
        self,
        filesystem: FileSystem,
        yaml_io: YAMLSerializer,
        output_formatter: OutputFormatter,
    ):
        self.fs = filesystem
        self.yaml = yaml_io
        self.formatter = output_formatter

    def handle(
        self,
        path: str,
        recursive: bool,
        dry_run: bool,
        format: str,
    ) -> str:
        """Execute scan command."""
        # 1. Find repository root
        repo_root = self.fs.find_repo_root(path or os.getcwd())

        # 2. Load config and index
        config_mgr = ConfigManager(self.fs, self.yaml, repo_root)
        config = config_mgr.load_config()

        index_mgr = IndexManager(self.fs, self.yaml, repo_root)
        index = index_mgr.load_index()

        # 3. Find all Markdown files
        scan_path = path or repo_root
        files = list(self.fs.walk_files(scan_path, "*.md", recursive))

        # 4. Parse metadata from each file
        metadata_parser = MetadataParser(self.fs)
        location_resolver = LocationResolver(self.fs)
        snippet_extractor = SnippetExtractor(self.fs)
        checksum_calc = ChecksumCalculator()

        nodes_added = []
        nodes_updated = []
        changed_nodes = set()

        for file_path in files:
            rel_path = str(Path(file_path).relative_to(repo_root))

            metadata_blocks = metadata_parser.parse_file(file_path)

            for metadata in metadata_blocks:
                # Resolve location
                location = location_resolver.resolve_location(
                    file_path, metadata.line_number
                )

                # Extract snippet and calculate checksum
                snippet = snippet_extractor.extract_snippet(file_path, location)
                checksum = checksum_calc.calculate_checksum(snippet)

                # Create or update node
                node_id = metadata.id
                if node_id == "auto":
                    # Generate next ID
                    id_gen = IDGenerator()
                    node_id = id_gen.next_id(metadata.type, index, config)

                now = datetime.now(timezone.utc).isoformat()

                node = Node(
                    id=node_id,
                    type=NodeType(metadata.type),
                    title=metadata.title,
                    file=rel_path,
                    location=location,
                    status=NodeStatus(metadata.status),
                    last_updated=now,
                    checksum=checksum,
                    llm_generated=metadata.llm_generated,
                    tags=metadata.tags,
                )

                # Check if node exists
                existing_node = index.nodes.get(node_id)
                if existing_node:
                    # Check if checksum changed
                    if existing_node.checksum != checksum:
                        changed_nodes.add(node_id)
                        nodes_updated.append(node_id)
                    index.nodes[node_id] = node
                else:
                    index.nodes[node_id] = node
                    nodes_added.append(node_id)

        # 5. Build links from metadata
        # ... (similar logic)

        # 6. Update sync status
        linking_engine = LinkingEngine()
        linking_engine.update_sync_status(index, changed_nodes)

        # 7. Save index (unless dry run)
        if not dry_run:
            index_mgr.save_index(index)

        # 8. Format output
        summary = {
            'files_scanned': len(files),
            'nodes_added': nodes_added,
            'nodes_updated': nodes_updated,
            'dry_run': dry_run,
        }

        return self.formatter.format_scan_result(summary, format)
```

---

## 6. Summary

This detailed design provides:

1. **Complete class specifications** with type hints and validation
2. **Algorithms** for key operations (parsing, linking, traversal)
3. **Data flow examples** showing how components interact
4. **Error handling** with custom exceptions
5. **Testing approach** for unit, integration, and E2E tests

The design is ready for implementation, with clear interfaces and responsibilities for each module.
