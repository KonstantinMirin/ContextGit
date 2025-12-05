"""Python file scanner.

contextgit:
  id: C-126
  type: code
  title: "Python Scanner - Docstring Metadata Extraction"
  status: active
  upstream: [SR-012]
  tags: [scanners, python, fr-14, multi-format]

Extracts contextgit metadata from Python files using:
- Module docstrings with 'contextgit:' YAML blocks
- Comment blocks with '# contextgit:' YAML blocks
"""

import re
from pathlib import Path
from typing import List

from contextgit.scanners.base import FileScanner, ExtractedMetadata
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.exceptions import InvalidMetadataError


class PythonScanner(FileScanner):
    """Scanner for Python files (.py, .pyw)."""

    def __init__(self, filesystem: FileSystem = None, yaml_serializer: YAMLSerializer = None):
        """
        Initialize PythonScanner.

        Args:
            filesystem: File system abstraction (default: creates new instance)
            yaml_serializer: YAML serializer (default: creates new instance)
        """
        self.fs = filesystem or FileSystem()
        self.yaml = yaml_serializer or YAMLSerializer()

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported Python extensions."""
        return ['.py', '.pyw']

    def extract_metadata(self, file_path: Path) -> List[ExtractedMetadata]:
        """
        Extract all contextgit metadata blocks from a Python file.

        Supports both module docstrings and comment blocks.

        Args:
            file_path: Path to Python file

        Returns:
            List of extracted metadata blocks

        Raises:
            InvalidMetadataError: If metadata is malformed
            FileNotFoundError: If file doesn't exist
        """
        content = self.fs.read_file(str(file_path))

        metadata_blocks = []

        # Try module docstring first
        docstring_block = self._parse_module_docstring(content)
        if docstring_block:
            metadata_blocks.append(docstring_block)

        # Parse comment blocks
        comment_blocks = self._parse_comment_blocks(content)
        metadata_blocks.extend(comment_blocks)

        return metadata_blocks

    def _parse_module_docstring(self, content: str) -> ExtractedMetadata | None:
        """Parse module docstring for contextgit metadata.

        Looks for triple-quoted strings at the start of the file containing
        'contextgit:' followed by YAML.
        """
        # Match module-level docstrings (triple quotes at start, allowing whitespace)
        # Supports both """ and '''
        pattern = r'^\s*("""|\'\'\')(.*?)\1'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return None

        docstring = match.group(2)
        raw_content = match.group(0)

        # Check if docstring contains 'contextgit:'
        if 'contextgit:' not in docstring:
            return None

        # Extract YAML after 'contextgit:'
        contextgit_pattern = r'contextgit:\s*\n(.*?)(?:\n\s*\n|\Z)'
        cg_match = re.search(contextgit_pattern, docstring, re.DOTALL)

        if not cg_match:
            return None

        yaml_content = cg_match.group(1)

        # Calculate line number (start of docstring)
        line_number = content[:match.start()].count('\n') + 1

        try:
            data = self.yaml.load_yaml(yaml_content)
            return self._extract_metadata(data, line_number, raw_content)
        except Exception as e:
            raise InvalidMetadataError(f"Invalid docstring metadata at line {line_number}: {e}")

    def _parse_comment_blocks(self, content: str) -> List[ExtractedMetadata]:
        """Parse comment blocks for contextgit metadata.

        Looks for comment blocks like:
        # contextgit:
        #   id: C-001
        #   type: code
        #   title: ...
        """
        blocks = []

        # Find comment blocks starting with '# contextgit:'
        # Pattern: # contextgit: followed by lines starting with #
        pattern = r'^# contextgit:\s*\n((?:^#.*\n)+)'
        matches = re.finditer(pattern, content, re.MULTILINE)

        for match in matches:
            comment_block = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            raw_content = match.group(0)

            # Remove leading '# ' from each line
            yaml_lines = []
            for line in comment_block.split('\n'):
                # Remove leading '# ' or '#'
                if line.startswith('# '):
                    yaml_lines.append(line[2:])
                elif line.startswith('#'):
                    yaml_lines.append(line[1:])
                else:
                    break  # Stop at first non-comment line

            yaml_content = '\n'.join(yaml_lines)

            try:
                data = self.yaml.load_yaml(yaml_content)
                metadata = self._extract_metadata(data, line_number, raw_content)
                blocks.append(metadata)
            except Exception as e:
                raise InvalidMetadataError(
                    f"Invalid comment block at line {line_number}: {e}"
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
