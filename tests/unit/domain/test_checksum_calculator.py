"""Unit tests for ChecksumCalculator."""

import time
import pytest
from contextgit.domain.checksum import ChecksumCalculator


class TestChecksumCalculator:
    """Tests for ChecksumCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create ChecksumCalculator instance."""
        return ChecksumCalculator()

    def test_calculate_checksum_simple_text(self, calculator):
        """Test checksum calculation for simple text."""
        text = "Hello, World!"
        checksum = calculator.calculate_checksum(text)

        # Should return 64-character hex digest
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum)

    def test_calculate_checksum_deterministic(self, calculator):
        """Test that same input produces same checksum."""
        text = "This is a test."
        checksum1 = calculator.calculate_checksum(text)
        checksum2 = calculator.calculate_checksum(text)

        assert checksum1 == checksum2

    def test_calculate_checksum_different_content(self, calculator):
        """Test that different content produces different checksums."""
        text1 = "First text"
        text2 = "Second text"

        checksum1 = calculator.calculate_checksum(text1)
        checksum2 = calculator.calculate_checksum(text2)

        assert checksum1 != checksum2

    def test_normalize_text_windows_line_endings(self, calculator):
        """Test normalization of Windows line endings."""
        text = "Line 1\r\nLine 2\r\nLine 3"
        checksum = calculator.calculate_checksum(text)

        # Should produce same checksum as Unix line endings
        text_unix = "Line 1\nLine 2\nLine 3"
        checksum_unix = calculator.calculate_checksum(text_unix)

        assert checksum == checksum_unix

    def test_normalize_text_mac_line_endings(self, calculator):
        """Test normalization of old Mac line endings."""
        text = "Line 1\rLine 2\rLine 3"
        checksum = calculator.calculate_checksum(text)

        # Should produce same checksum as Unix line endings
        text_unix = "Line 1\nLine 2\nLine 3"
        checksum_unix = calculator.calculate_checksum(text_unix)

        assert checksum == checksum_unix

    def test_normalize_text_strips_line_whitespace(self, calculator):
        """Test that leading/trailing whitespace is stripped from lines."""
        text = "  Line 1  \n  Line 2  \n  Line 3  "
        checksum = calculator.calculate_checksum(text)

        # Should produce same checksum as stripped text
        text_stripped = "Line 1\nLine 2\nLine 3"
        checksum_stripped = calculator.calculate_checksum(text_stripped)

        assert checksum == checksum_stripped

    def test_normalize_text_removes_leading_empty_lines(self, calculator):
        """Test that empty lines at start are removed."""
        text = "\n\nLine 1\nLine 2"
        checksum = calculator.calculate_checksum(text)

        # Should produce same checksum without leading empty lines
        text_no_leading = "Line 1\nLine 2"
        checksum_no_leading = calculator.calculate_checksum(text_no_leading)

        assert checksum == checksum_no_leading

    def test_normalize_text_removes_trailing_empty_lines(self, calculator):
        """Test that empty lines at end are removed."""
        text = "Line 1\nLine 2\n\n\n"
        checksum = calculator.calculate_checksum(text)

        # Should produce same checksum without trailing empty lines
        text_no_trailing = "Line 1\nLine 2"
        checksum_no_trailing = calculator.calculate_checksum(text_no_trailing)

        assert checksum == checksum_no_trailing

    def test_normalize_text_preserves_internal_empty_lines(self, calculator):
        """Test that empty lines in the middle are preserved."""
        text = "Line 1\n\nLine 3"
        checksum = calculator.calculate_checksum(text)

        # Should be different from text without internal empty line
        text_no_empty = "Line 1\nLine 3"
        checksum_no_empty = calculator.calculate_checksum(text_no_empty)

        assert checksum != checksum_no_empty

    def test_normalize_text_complex_whitespace(self, calculator):
        """Test normalization with complex whitespace patterns."""
        text = "\n\n  Line 1  \r\n  \r\n  Line 2  \n\n"
        checksum = calculator.calculate_checksum(text)

        # Should normalize to simple form
        text_normalized = "Line 1\n\nLine 2"
        checksum_normalized = calculator.calculate_checksum(text_normalized)

        assert checksum == checksum_normalized

    def test_compare_checksums_identical(self, calculator):
        """Test comparing identical checksums."""
        checksum = "abc123def456"
        result = calculator.compare_checksums(checksum, checksum)
        assert result is True

    def test_compare_checksums_different(self, calculator):
        """Test comparing different checksums."""
        checksum1 = "abc123def456"
        checksum2 = "xyz789ghi012"
        result = calculator.compare_checksums(checksum1, checksum2)
        assert result is False

    def test_empty_text(self, calculator):
        """Test checksum calculation for empty text."""
        text = ""
        checksum = calculator.calculate_checksum(text)

        # Should return valid checksum even for empty string
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum)

    def test_empty_text_with_whitespace(self, calculator):
        """Test that text with only whitespace normalizes to empty."""
        text = "   \n\n  \r\n  "
        checksum = calculator.calculate_checksum(text)

        # Should produce same checksum as truly empty text
        text_empty = ""
        checksum_empty = calculator.calculate_checksum(text_empty)

        assert checksum == checksum_empty

    def test_unicode_text(self, calculator):
        """Test checksum calculation with Unicode characters."""
        text = "Hello 世界 🌍"
        checksum = calculator.calculate_checksum(text)

        # Should handle Unicode correctly
        assert len(checksum) == 64

        # Same Unicode should produce same checksum
        checksum2 = calculator.calculate_checksum(text)
        assert checksum == checksum2

    def test_multiline_markdown_snippet(self, calculator):
        """Test with realistic Markdown content."""
        text = """
# Business Requirement: User Authentication

## Description
Users must be able to log in securely.

## Acceptance Criteria
- [ ] Password hashing
- [ ] Session management
"""
        checksum = calculator.calculate_checksum(text)
        assert len(checksum) == 64

        # Should be deterministic
        checksum2 = calculator.calculate_checksum(text)
        assert checksum == checksum2

    def test_performance_small_snippet(self, calculator):
        """Test that small snippets (<1KB) are processed in <10ms."""
        # Create ~500 byte snippet
        text = "This is a test line.\n" * 25

        start = time.perf_counter()
        for _ in range(10):  # Run 10 times to get average
            calculator.calculate_checksum(text)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / 10) * 1000
        assert avg_time_ms < 10, f"Average time {avg_time_ms:.2f}ms exceeds 10ms target"

    def test_performance_typical_snippet(self, calculator):
        """Test that typical snippets (~5KB) are processed in <10ms."""
        # Create ~5KB snippet (typical requirement/doc section)
        text = "This is a test line with some content.\n" * 125

        assert len(text) < 5000, "Test snippet should be under 5KB"

        start = time.perf_counter()
        for _ in range(10):  # Run 10 times to get average
            calculator.calculate_checksum(text)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / 10) * 1000
        assert avg_time_ms < 10, f"Average time {avg_time_ms:.2f}ms exceeds 10ms target"

    def test_known_checksum_value(self, calculator):
        """Test against a known SHA-256 checksum value."""
        # The SHA-256 of "Hello, World!" (without normalization needed) is:
        text = "Hello, World!"
        expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"

        checksum = calculator.calculate_checksum(text)
        assert checksum == expected

    def test_internal_method_normalize_text(self, calculator):
        """Test the _normalize_text method directly."""
        text = "\n\n  Hello  \r\n  World  \n\n"
        normalized = calculator._normalize_text(text)

        assert normalized == "Hello\nWorld"

    def test_tabs_and_spaces_normalization(self, calculator):
        """Test that tabs and spaces are normalized."""
        text1 = "\tLine 1\t\n  Line 2  "
        text2 = "Line 1\nLine 2"

        checksum1 = calculator.calculate_checksum(text1)
        checksum2 = calculator.calculate_checksum(text2)

        assert checksum1 == checksum2

    def test_real_world_requirement_snippet(self, calculator):
        """Test with a real-world requirement text."""
        text = """
## FR-1: Initialize Project

The system shall provide a command to initialize a new contextgit project.

**Acceptance Criteria:**
- Creates `.contextgit/` directory
- Creates empty `requirements_index.yaml`
- Creates default `config.yaml`
- Fails gracefully if project already initialized

**Priority:** Critical
**Status:** Draft
"""
        checksum1 = calculator.calculate_checksum(text)

        # Slight modification should change checksum
        text_modified = text.replace("Critical", "High")
        checksum2 = calculator.calculate_checksum(text_modified)

        assert checksum1 != checksum2

        # Whitespace changes should NOT change checksum
        text_whitespace = text + "\n\n   \n"
        checksum3 = calculator.calculate_checksum(text_whitespace)

        assert checksum1 == checksum3
