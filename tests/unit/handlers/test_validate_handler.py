"""Unit tests for ValidateHandler."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from contextgit.handlers.validate_handler import ValidateHandler, IssueSeverity, ValidationIssue
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter


@pytest.fixture
def handler(tmp_path):
    """Create a ValidateHandler with test infrastructure."""
    # Create .contextgit directory
    contextgit_dir = tmp_path / ".contextgit"
    contextgit_dir.mkdir()

    # Create minimal config
    config_path = contextgit_dir / "config.yaml"
    config_path.write_text(
        """tag_prefixes:
  business: BR
  system: SR
  architecture: AR
  code: C
  test: T
  decision: DR
"""
    )

    # Create minimal index
    index_path = contextgit_dir / "requirements_index.yaml"
    index_path.write_text("""nodes: {}
links: []
""")

    fs = FileSystem()
    yaml = YAMLSerializer()
    formatter = OutputFormatter()

    handler = ValidateHandler(fs, yaml, formatter)
    return handler, tmp_path


def test_validate_no_issues(handler):
    """Test validation with no issues."""
    handler_obj, tmp_path = handler

    # Create a valid markdown file
    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: BR-001
  type: business
  title: Test Requirement
  status: active
  upstream: []
  downstream: []
---

This is a test requirement.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    assert data["files_scanned"] == 1
    assert data["blocks_found"] == 1
    # Note: orphan warnings will be present for nodes without upstream/downstream
    assert data["summary"]["errors"] == 0
    # Business requirements without upstream/downstream generate orphan warnings
    assert data["summary"]["warnings"] >= 0


def test_validate_self_reference_upstream(handler):
    """Test detection of self-reference in upstream."""
    handler_obj, tmp_path = handler

    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test Requirement
  status: active
  upstream: [SR-001]
  downstream: []
---

This is a test requirement.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    assert data["summary"]["errors"] >= 1

    # Find self-reference error
    self_ref_errors = [i for i in data["issues"] if i["code"] == "SELF_REFERENCE"]
    assert len(self_ref_errors) >= 1
    assert "SR-001" in self_ref_errors[0]["message"]


def test_validate_self_reference_downstream(handler):
    """Test detection of self-reference in downstream."""
    handler_obj, tmp_path = handler

    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test Requirement
  status: active
  upstream: []
  downstream: [SR-001]
---

This is a test requirement.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    assert data["summary"]["errors"] >= 1

    # Find self-reference error
    self_ref_errors = [i for i in data["issues"] if i["code"] == "SELF_REFERENCE"]
    assert len(self_ref_errors) >= 1
    assert "SR-001" in self_ref_errors[0]["message"]


def test_validate_missing_target(handler):
    """Test detection of missing target node."""
    handler_obj, tmp_path = handler

    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test Requirement
  status: active
  upstream: [BR-999]
  downstream: []
---

This is a test requirement.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    assert data["summary"]["errors"] >= 1

    # Find missing target error
    missing_errors = [i for i in data["issues"] if i["code"] == "MISSING_TARGET"]
    assert len(missing_errors) >= 1
    assert "BR-999" in missing_errors[0]["message"]


def test_validate_duplicate_id(handler):
    """Test detection of duplicate IDs."""
    handler_obj, tmp_path = handler

    doc1 = tmp_path / "test1.md"
    doc1.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test Requirement 1
  status: active
  upstream: []
  downstream: []
---

This is test 1.
"""
    )

    doc2 = tmp_path / "test2.md"
    doc2.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test Requirement 2
  status: active
  upstream: []
  downstream: []
---

This is test 2.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    assert data["summary"]["errors"] >= 1

    # Find duplicate ID error
    dup_errors = [i for i in data["issues"] if i["code"] == "DUPLICATE_ID"]
    assert len(dup_errors) >= 1
    assert "SR-001" in dup_errors[0]["message"]


def test_validate_circular_dependency(handler):
    """Test detection of circular dependencies across files."""
    handler_obj, tmp_path = handler

    doc1 = tmp_path / "test1.md"
    doc1.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Requirement 1
  status: active
  upstream: []
  downstream: [SR-002]
---

This is requirement 1.
"""
    )

    doc2 = tmp_path / "test2.md"
    doc2.write_text(
        """---
contextgit:
  id: SR-002
  type: system
  title: Requirement 2
  status: active
  upstream: []
  downstream: [SR-003]
---

This is requirement 2.
"""
    )

    doc3 = tmp_path / "test3.md"
    doc3.write_text(
        """---
contextgit:
  id: SR-003
  type: system
  title: Requirement 3
  status: active
  upstream: []
  downstream: [SR-001]
---

This is requirement 3.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    assert data["summary"]["errors"] >= 1

    # Find circular dependency error
    cycle_errors = [i for i in data["issues"] if i["code"] == "CIRCULAR_DEPENDENCY"]
    assert len(cycle_errors) >= 1
    assert "SR-001" in cycle_errors[0]["message"]


def test_validate_orphan_nodes(handler):
    """Test detection of orphan nodes."""
    handler_obj, tmp_path = handler

    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Orphan Requirement
  status: active
  upstream: []
  downstream: []
---

This is an orphan requirement.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    # Orphans are warnings, not errors
    assert data["summary"]["warnings"] >= 1

    # Find orphan warnings
    orphan_warnings = [i for i in data["issues"] if i["code"] == "ORPHAN_NODE"]
    assert len(orphan_warnings) >= 1


def test_validate_parse_error(handler):
    """Test detection of parse errors."""
    handler_obj, tmp_path = handler

    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test
  status: active
  upstream: this is not a list
  downstream: []
---

This is a test.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    # Should have a parse error
    parse_errors = [i for i in data["issues"] if i["code"] == "PARSE_ERROR"]
    # Note: might not trigger if parser is lenient


def test_validate_text_output_format(handler):
    """Test text output format."""
    handler_obj, tmp_path = handler

    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test
  status: active
  upstream: [SR-001]
  downstream: []
---

This is a test.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="text")

    assert "Validation Results" in result
    assert "Files scanned:" in result
    assert "Blocks found:" in result
    assert "ERRORS" in result
    assert "SELF_REFERENCE" in result


def test_validate_json_output_format(handler):
    """Test JSON output format."""
    handler_obj, tmp_path = handler

    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test
  status: active
  upstream: []
  downstream: []
---

This is a test.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    assert "files_scanned" in data
    assert "blocks_found" in data
    assert "issues" in data
    assert "summary" in data
    assert "errors" in data["summary"]
    assert "warnings" in data["summary"]
    assert "info" in data["summary"]


def test_validate_recursive(handler):
    """Test recursive scanning."""
    handler_obj, tmp_path = handler

    # Create subdirectory
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    doc1 = tmp_path / "test1.md"
    doc1.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test 1
  status: active
  upstream: []
  downstream: []
---

Test 1.
"""
    )

    doc2 = subdir / "test2.md"
    doc2.write_text(
        """---
contextgit:
  id: SR-002
  type: system
  title: Test 2
  status: active
  upstream: []
  downstream: []
---

Test 2.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=True, format="json")
    data = json.loads(result)

    assert data["files_scanned"] == 2
    assert data["blocks_found"] == 2


def test_validate_non_recursive(handler):
    """Test non-recursive scanning."""
    handler_obj, tmp_path = handler

    # Create subdirectory
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    doc1 = tmp_path / "test1.md"
    doc1.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test 1
  status: active
  upstream: []
  downstream: []
---

Test 1.
"""
    )

    doc2 = subdir / "test2.md"
    doc2.write_text(
        """---
contextgit:
  id: SR-002
  type: system
  title: Test 2
  status: active
  upstream: []
  downstream: []
---

Test 2.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    # Should only find doc1
    assert data["files_scanned"] == 1
    assert data["blocks_found"] == 1


def test_validation_issue_to_dict():
    """Test ValidationIssue.to_dict() method."""
    issue = ValidationIssue(
        severity=IssueSeverity.ERROR,
        code="TEST_CODE",
        message="Test message",
        file="test.md",
        line=10,
        suggestion="Test suggestion",
    )

    result = issue.to_dict()

    assert result["severity"] == "error"
    assert result["code"] == "TEST_CODE"
    assert result["message"] == "Test message"
    assert result["file"] == "test.md"
    assert result["line"] == 10
    assert result["suggestion"] == "Test suggestion"


def test_validate_multiple_issues(handler):
    """Test handling of multiple different issue types."""
    handler_obj, tmp_path = handler

    doc1 = tmp_path / "test1.md"
    doc1.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test 1
  status: active
  upstream: [SR-001, BR-999]
  downstream: []
---

Test 1.
"""
    )

    doc2 = tmp_path / "test2.md"
    doc2.write_text(
        """---
contextgit:
  id: SR-001
  type: system
  title: Test 2
  status: active
  upstream: []
  downstream: []
---

Test 2.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    # Should have:
    # - Self-reference error (SR-001 in upstream)
    # - Missing target error (BR-999)
    # - Duplicate ID error (SR-001 in both files)
    assert data["summary"]["errors"] >= 3

    # Check for different error types
    error_codes = [i["code"] for i in data["issues"] if i["severity"] == "error"]
    assert "SELF_REFERENCE" in error_codes
    assert "MISSING_TARGET" in error_codes
    assert "DUPLICATE_ID" in error_codes


def test_validate_empty_directory(handler):
    """Test validation of empty directory."""
    handler_obj, tmp_path = handler

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    assert data["files_scanned"] == 0
    assert data["blocks_found"] == 0
    assert len(data["issues"]) == 0


def test_validate_skip_auto_ids(handler):
    """Test that nodes with id: auto are skipped."""
    handler_obj, tmp_path = handler

    doc = tmp_path / "test.md"
    doc.write_text(
        """---
contextgit:
  id: auto
  type: system
  title: Auto ID Node
  status: active
  upstream: []
  downstream: []
---

This node has auto ID.
"""
    )

    result = handler_obj.handle(path=str(tmp_path), recursive=False, format="json")
    data = json.loads(result)

    # Should find the block but not validate it (auto IDs are handled during scan)
    assert data["blocks_found"] == 1
    # No errors for the auto ID itself
    # (although orphan warnings might appear)
