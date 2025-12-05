"""Tests for Markdown file scanner."""

import pytest
from pathlib import Path
from contextgit.scanners.markdown import MarkdownScanner
from contextgit.scanners.base import ExtractedMetadata
from contextgit.exceptions import InvalidMetadataError


class TestMarkdownScanner:
    """Test cases for MarkdownScanner."""

    def test_supported_extensions(self):
        """Test that scanner reports correct extensions."""
        scanner = MarkdownScanner()
        assert scanner.supported_extensions == ['.md', '.markdown']

    def test_parse_frontmatter(self, tmp_path):
        """Test parsing YAML frontmatter."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
contextgit:
  id: BR-001
  type: business
  title: User Authentication
  status: active
  upstream: []
  tags: [security, auth]
---

# User Authentication

Content here.
""")

        scanner = MarkdownScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "BR-001"
        assert metadata.type == "business"
        assert metadata.title == "User Authentication"
        assert metadata.status == "active"
        assert metadata.tags == ["security", "auth"]
        assert metadata.line_number == 1

    def test_parse_inline_html_comment(self, tmp_path):
        """Test parsing inline HTML comment blocks."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""# Requirements

<!-- contextgit
id: SR-001
type: system
title: API Endpoint
upstream: [BR-001]
status: draft
-->

Some content here.
""")

        scanner = MarkdownScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "SR-001"
        assert metadata.type == "system"
        assert metadata.title == "API Endpoint"
        assert metadata.upstream == ["BR-001"]
        assert metadata.status == "draft"

    def test_parse_multiple_blocks(self, tmp_path):
        """Test parsing multiple metadata blocks in one file."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
contextgit:
  id: BR-001
  type: business
  title: First Requirement
---

# First Requirement

<!-- contextgit
id: SR-001
type: system
title: Second Requirement
upstream: [BR-001]
-->

## Implementation

<!-- contextgit
id: C-001
type: code
title: Third Requirement
upstream: [SR-001]
-->
""")

        scanner = MarkdownScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 3
        assert results[0].id == "BR-001"
        assert results[1].id == "SR-001"
        assert results[2].id == "C-001"

    def test_missing_required_field(self, tmp_path):
        """Test error when required field is missing."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
contextgit:
  id: BR-001
  type: business
---
""")

        scanner = MarkdownScanner()
        with pytest.raises(InvalidMetadataError, match="Missing 'title' field"):
            scanner.extract_metadata(file_path)

    def test_no_metadata(self, tmp_path):
        """Test file with no metadata returns empty list."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""# Regular Markdown

Just content, no metadata.
""")

        scanner = MarkdownScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_frontmatter_without_contextgit(self, tmp_path):
        """Test frontmatter without contextgit key is ignored."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
title: Some Document
author: John Doe
---

Content here.
""")

        scanner = MarkdownScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_upstream_downstream_string_to_list(self, tmp_path):
        """Test that string upstream/downstream values are converted to lists."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
contextgit:
  id: SR-001
  type: system
  title: Test
  upstream: BR-001
  downstream: C-001
---
""")

        scanner = MarkdownScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].upstream == ["BR-001"]
        assert results[0].downstream == ["C-001"]

    def test_llm_generated_flag(self, tmp_path):
        """Test llm_generated flag is parsed correctly."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
contextgit:
  id: BR-001
  type: business
  title: Test
  llm_generated: true
---
""")

        scanner = MarkdownScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].llm_generated is True

    def test_raw_content_captured(self, tmp_path):
        """Test that raw_content is captured for snippet extraction."""
        file_path = tmp_path / "test.md"
        file_path.write_text("""<!-- contextgit
id: SR-001
type: system
title: Test
-->
""")

        scanner = MarkdownScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].raw_content != ""
        assert "contextgit" in results[0].raw_content
