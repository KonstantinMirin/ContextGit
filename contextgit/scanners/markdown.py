"""Markdown file scanner.

Extracts contextgit metadata from Markdown files using:
- YAML frontmatter (--- delimited blocks at file start)
- Inline HTML comments (<!-- contextgit ... -->)
"""

import re
from pathlib import Path
from typing import List

from contextgit.scanners.base import FileScanner, ExtractedMetadata
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.exceptions import InvalidMetadataError


class MarkdownScanner(FileScanner):
    """Scanner for Markdown files (.md, .markdown)."""

    def __init__(self, filesystem: FileSystem = None, yaml_serializer: YAMLSerializer = None):
        """
        Initialize MarkdownScanner.

        Args:
            filesystem: File system abstraction (default: creates new instance)
            yaml_serializer: YAML serializer (default: creates new instance)
        """
        self.fs = filesystem or FileSystem()
        self.yaml = yaml_serializer or YAMLSerializer()

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported Markdown extensions."""
        return ['.md', '.markdown']

    def extract_metadata(self, file_path: Path) -> List[ExtractedMetadata]:
        """
        Extract all contextgit metadata blocks from a Markdown file.

        Supports both YAML frontmatter and inline HTML comments.

        Args:
            file_path: Path to Markdown file

        Returns:
            List of extracted metadata blocks

        Raises:
            InvalidMetadataError: If metadata is malformed
            FileNotFoundError: If file doesn't exist
        """
        content = self.fs.read_file(str(file_path))

        metadata_blocks = []

        # Try frontmatter first
        frontmatter = self._parse_frontmatter(content)
        if frontmatter:
            metadata_blocks.append(frontmatter)

        # Parse inline blocks
        inline_blocks = self._parse_inline_blocks(content)
        metadata_blocks.extend(inline_blocks)

        return metadata_blocks

    def _parse_frontmatter(self, content: str) -> ExtractedMetadata | None:
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
            data = self.yaml.load_yaml(yaml_content)

            # Check for 'contextgit' key
            if 'contextgit' not in data:
                return None

            cg_data = data['contextgit']

            # Extract raw content for snippet (include the frontmatter block)
            raw_content = '\n'.join(lines[0:end_idx+1])

            return self._extract_metadata(cg_data, line_number=1, raw_content=raw_content)

        except Exception as e:
            raise InvalidMetadataError(f"Invalid frontmatter: {e}")

    def _parse_inline_blocks(self, content: str) -> List[ExtractedMetadata]:
        """Parse inline HTML comment blocks."""
        blocks = []

        # Regex to find <!-- contextgit ... -->
        pattern = r'<!--\s*contextgit\s*\n(.*?)\n\s*-->'
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            yaml_content = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            raw_content = match.group(0)

            try:
                data = self.yaml.load_yaml(yaml_content)
                metadata = self._extract_metadata(data, line_number, raw_content)
                blocks.append(metadata)
            except Exception as e:
                raise InvalidMetadataError(
                    f"Invalid inline block at line {line_number}: {e}"
                )

        return blocks

    def _extract_metadata(
        self,
        data: dict,
        line_number: int,
        raw_content: str = ""
    ) -> ExtractedMetadata:
        """Extract and validate metadata from parsed YAML."""
        # Required fields
        if 'id' not in data:
            raise InvalidMetadataError(f"Missing 'id' field at line {line_number}")
        if 'type' not in data:
            raise InvalidMetadataError(f"Missing 'type' field at line {line_number}")
        if 'title' not in data:
            raise InvalidMetadataError(f"Missing 'title' field at line {line_number}")

        # Ensure upstream/downstream are lists
        upstream = data.get('upstream', [])
        if isinstance(upstream, str):
            upstream = [upstream]
        elif not isinstance(upstream, list):
            upstream = []

        downstream = data.get('downstream', [])
        if isinstance(downstream, str):
            downstream = [downstream]
        elif not isinstance(downstream, list):
            downstream = []

        tags = data.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = []

        return ExtractedMetadata(
            id=data['id'],
            type=data['type'],
            title=data['title'],
            upstream=upstream,
            downstream=downstream,
            status=data.get('status', 'active'),
            tags=tags,
            llm_generated=data.get('llm_generated', False),
            line_number=line_number,
            raw_content=raw_content,
        )
