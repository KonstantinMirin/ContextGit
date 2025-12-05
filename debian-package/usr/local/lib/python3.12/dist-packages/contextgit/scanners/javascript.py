"""JavaScript/TypeScript file scanner.

contextgit:
  id: C-127
  type: code
  title: "JavaScript Scanner - JSDoc Metadata Extraction"
  status: active
  upstream: [SR-012]
  tags: [scanners, javascript, typescript, fr-14, multi-format]

Extracts contextgit metadata from JavaScript and TypeScript files using:
- JSDoc-style comment blocks with @contextgit tag
"""

import re
from pathlib import Path
from typing import List

from contextgit.scanners.base import FileScanner, ExtractedMetadata
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.exceptions import InvalidMetadataError


class JavaScriptScanner(FileScanner):
    """Scanner for JavaScript and TypeScript files."""

    def __init__(self, filesystem: FileSystem = None, yaml_serializer: YAMLSerializer = None):
        """
        Initialize JavaScriptScanner.

        Args:
            filesystem: File system abstraction (default: creates new instance)
            yaml_serializer: YAML serializer (default: creates new instance)
        """
        self.fs = filesystem or FileSystem()
        self.yaml = yaml_serializer or YAMLSerializer()

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported JavaScript/TypeScript extensions."""
        return ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']

    def extract_metadata(self, file_path: Path) -> List[ExtractedMetadata]:
        """
        Extract all contextgit metadata blocks from a JavaScript/TypeScript file.

        Supports JSDoc-style comment blocks with @contextgit tag.

        Args:
            file_path: Path to JavaScript/TypeScript file

        Returns:
            List of extracted metadata blocks

        Raises:
            InvalidMetadataError: If metadata is malformed
            FileNotFoundError: If file doesn't exist
        """
        content = self.fs.read_file(str(file_path))

        # Parse JSDoc blocks with @contextgit
        return self._parse_jsdoc_blocks(content)

    def _parse_jsdoc_blocks(self, content: str) -> List[ExtractedMetadata]:
        """Parse JSDoc comment blocks for contextgit metadata.

        Looks for /** ... */ blocks containing '@contextgit' followed by YAML.

        Example:
        /**
         * @contextgit
         * id: C-017
         * type: code
         * title: Frontend Auth
         */
        """
        blocks = []

        # Find JSDoc blocks (/** ... */)
        # Pattern: /** followed by content and closing */
        pattern = r'/\*\*(.*?)\*/'
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            jsdoc_content = match.group(1)

            # Check if it contains @contextgit
            if '@contextgit' not in jsdoc_content:
                continue

            line_number = content[:match.start()].count('\n') + 1
            raw_content = match.group(0)

            # Extract YAML after @contextgit
            # Remove leading * and whitespace from each line
            lines = jsdoc_content.split('\n')
            yaml_lines = []
            in_contextgit = False

            for line in lines:
                # Remove leading whitespace and asterisk
                stripped = line.strip()
                if stripped.startswith('*'):
                    stripped = stripped[1:].lstrip()

                # Check for @contextgit marker
                if '@contextgit' in stripped:
                    in_contextgit = True
                    continue

                # If we're in contextgit section, collect YAML lines
                if in_contextgit:
                    # Stop at next @ tag or empty line after content started
                    if stripped.startswith('@') and stripped != '@contextgit':
                        break
                    yaml_lines.append(stripped)

            # Join YAML lines
            yaml_content = '\n'.join(yaml_lines).strip()

            if not yaml_content:
                continue

            try:
                data = self.yaml.load_yaml(yaml_content)
                metadata = self._extract_metadata(data, line_number, raw_content)
                blocks.append(metadata)
            except Exception as e:
                raise InvalidMetadataError(
                    f"Invalid JSDoc @contextgit block at line {line_number}: {e}"
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
