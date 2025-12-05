"""Tests for Python file scanner."""

import pytest
from pathlib import Path
from contextgit.scanners.python import PythonScanner
from contextgit.scanners.base import ExtractedMetadata
from contextgit.exceptions import InvalidMetadataError


class TestPythonScanner:
    """Test cases for PythonScanner."""

    def test_supported_extensions(self):
        """Test that scanner reports correct extensions."""
        scanner = PythonScanner()
        assert scanner.supported_extensions == ['.py', '.pyw']

    def test_parse_module_docstring_double_quotes(self, tmp_path):
        """Test parsing module docstring with double quotes."""
        file_path = tmp_path / "test.py"
        file_path.write_text('''"""
Module for script generation.

contextgit:
  id: C-015
  type: code
  title: Script Generation
  upstream: [SR-012]
  status: active
"""

def generate_script():
    pass
''')

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "C-015"
        assert metadata.type == "code"
        assert metadata.title == "Script Generation"
        assert metadata.upstream == ["SR-012"]
        assert metadata.status == "active"

    def test_parse_module_docstring_single_quotes(self, tmp_path):
        """Test parsing module docstring with single quotes."""
        file_path = tmp_path / "test.py"
        file_path.write_text("""'''
Module for validation.

contextgit:
  id: C-016
  type: code
  title: Validation Stage
  tags: [validation, pipeline]
'''

class Validator:
    pass
""")

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "C-016"
        assert metadata.type == "code"
        assert metadata.title == "Validation Stage"
        assert metadata.tags == ["validation", "pipeline"]

    def test_parse_comment_block(self, tmp_path):
        """Test parsing comment block format."""
        file_path = tmp_path / "test.py"
        file_path.write_text("""import sys

# contextgit:
#   id: C-017
#   type: code
#   title: Data Processing Function
#   upstream: [SR-005]
#   status: draft

def process_data(data):
    return data.strip()
""")

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "C-017"
        assert metadata.type == "code"
        assert metadata.title == "Data Processing Function"
        assert metadata.upstream == ["SR-005"]
        assert metadata.status == "draft"

    def test_parse_multiple_blocks(self, tmp_path):
        """Test parsing multiple metadata blocks in one file."""
        file_path = tmp_path / "test.py"
        file_path.write_text('''"""
Module docstring.

contextgit:
  id: C-001
  type: code
  title: Module Level
"""

# contextgit:
#   id: C-002
#   type: code
#   title: Function Level

def some_function():
    pass
''')

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 2
        assert results[0].id == "C-001"
        assert results[1].id == "C-002"

    def test_missing_required_field(self, tmp_path):
        """Test error when required field is missing."""
        file_path = tmp_path / "test.py"
        file_path.write_text('''"""
contextgit:
  id: C-001
  type: code
"""
''')

        scanner = PythonScanner()
        with pytest.raises(InvalidMetadataError, match="Missing 'title' field"):
            scanner.extract_metadata(file_path)

    def test_no_metadata(self, tmp_path):
        """Test file with no metadata returns empty list."""
        file_path = tmp_path / "test.py"
        file_path.write_text("""'''Regular module docstring.'''

def main():
    pass
""")

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_docstring_without_contextgit(self, tmp_path):
        """Test docstring without contextgit: is ignored."""
        file_path = tmp_path / "test.py"
        file_path.write_text('''"""
This is a regular module docstring.
It doesn't contain any metadata.
"""

def main():
    pass
''')

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_upstream_downstream_string_to_list(self, tmp_path):
        """Test that string upstream/downstream values are converted to lists."""
        file_path = tmp_path / "test.py"
        file_path.write_text('''"""
contextgit:
  id: C-001
  type: code
  title: Test
  upstream: SR-001
  downstream: T-001
"""
''')

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].upstream == ["SR-001"]
        assert results[0].downstream == ["T-001"]

    def test_comment_block_with_no_space_after_hash(self, tmp_path):
        """Test comment block parsing handles # without space."""
        file_path = tmp_path / "test.py"
        file_path.write_text("""#contextgit:
#id: C-001
#type: code
#title: Test Function
""")

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].id == "C-001"

    def test_indented_module_docstring(self, tmp_path):
        """Test module docstring with leading whitespace."""
        file_path = tmp_path / "test.py"
        file_path.write_text('''    """
    contextgit:
      id: C-001
      type: code
      title: Test
    """
''')

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        # Should still parse module docstrings even with indentation
        assert len(results) == 1
        assert results[0].id == "C-001"

    def test_llm_generated_flag(self, tmp_path):
        """Test llm_generated flag is parsed correctly."""
        file_path = tmp_path / "test.py"
        file_path.write_text('''"""
contextgit:
  id: C-001
  type: code
  title: Test
  llm_generated: true
"""
''')

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].llm_generated is True

    def test_raw_content_captured(self, tmp_path):
        """Test that raw_content is captured for snippet extraction."""
        file_path = tmp_path / "test.py"
        file_path.write_text('''"""
contextgit:
  id: C-001
  type: code
  title: Test
"""
''')

        scanner = PythonScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].raw_content != ""
        assert "contextgit" in results[0].raw_content
