"""Gherkin/Cucumber feature file scanner.

contextgit:
  id: C-128
  type: code
  title: "Gherkin Scanner - Feature File Metadata Extraction"
  status: active
  upstream: [SR-012]
  tags: [scanners, gherkin, cucumber, fr-14, multi-format]

Extracts contextgit metadata from Gherkin feature files using:
- Comment blocks with '# @contextgit' marker followed by YAML lines
"""

import re
from pathlib import Path
from typing import List

from contextgit.scanners.base import FileScanner, ExtractedMetadata
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.exceptions import InvalidMetadataError


class GherkinScanner(FileScanner):
    """Scanner for Gherkin/Cucumber feature files (.feature)."""

    def __init__(self, filesystem: FileSystem = None, yaml_serializer: YAMLSerializer = None):
        """
        Initialize GherkinScanner.

        Args:
            filesystem: File system abstraction (default: creates new instance)
            yaml_serializer: YAML serializer (default: creates new instance)
        """
        self.fs = filesystem or FileSystem()
        self.yaml = yaml_serializer or YAMLSerializer()

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported Gherkin extensions."""
        return ['.feature']

    def extract_metadata(self, file_path: Path) -> List[ExtractedMetadata]:
        """
        Extract all contextgit metadata blocks from a Gherkin feature file.

        Supports comment blocks with # @contextgit marker.

        Args:
            file_path: Path to Gherkin feature file

        Returns:
            List of extracted metadata blocks

        Raises:
            InvalidMetadataError: If metadata is malformed
            FileNotFoundError: If file doesn't exist
        """
        content = self.fs.read_file(str(file_path))

        # Parse comment blocks with # @contextgit
        return self._parse_comment_blocks(content)

    def _parse_comment_blocks(self, content: str) -> List[ExtractedMetadata]:
        """Parse comment blocks for contextgit metadata.

        Looks for comment blocks like:
        # @contextgit
        # id: T-001
        # type: test
        # title: Login Feature Tests

        Handles both file-level (no indentation) and indented blocks
        (before Scenario).

        Example:
            # @contextgit
            # id: T-001
            # type: test
            # title: Feature Level

            Feature: User Login

              # @contextgit
              # id: T-002
              # type: test
              # title: Scenario Level

              Scenario: Successful login
        """
        blocks = []

        # Find comment blocks starting with '# @contextgit'
        # Pattern: captures optional leading indentation, then # @contextgit marker,
        # followed by subsequent comment lines with the same indentation
        # Using a line-by-line approach for better indentation handling
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()

            # Check for @contextgit marker
            if stripped.startswith('# @contextgit') or stripped == '#@contextgit':
                # Found a contextgit block
                line_number = i + 1  # 1-based line numbers
                indent = len(line) - len(stripped)
                raw_lines = [line]
                yaml_lines = []

                # Collect subsequent comment lines
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    next_stripped = next_line.lstrip()

                    # Check if this is a continuation comment line
                    # Must start with # and have same or greater indentation
                    if not next_stripped.startswith('#'):
                        break

                    next_indent = len(next_line) - len(next_stripped)

                    # Allow same indentation or slightly more (for YAML structure)
                    if next_indent < indent:
                        break

                    raw_lines.append(next_line)

                    # Extract YAML content from comment
                    # Remove '# ' or '#' prefix
                    if next_stripped.startswith('# '):
                        yaml_content = next_stripped[2:]
                    elif next_stripped.startswith('#'):
                        yaml_content = next_stripped[1:]
                    else:
                        yaml_content = next_stripped

                    # Skip empty comment lines but don't break
                    if yaml_content.strip():
                        yaml_lines.append(yaml_content)

                    j += 1

                raw_content = '\n'.join(raw_lines)
                yaml_content = '\n'.join(yaml_lines)

                if yaml_content.strip():
                    try:
                        data = self.yaml.load_yaml(yaml_content)
                        metadata = self._extract_metadata(data, line_number, raw_content)
                        blocks.append(metadata)
                    except Exception as e:
                        raise InvalidMetadataError(
                            f"Invalid comment block at line {line_number}: {e}"
                        )

                i = j
            else:
                i += 1

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
