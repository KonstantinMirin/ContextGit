"""Tests for scanner registry."""

import pytest
from pathlib import Path
from contextgit.scanners import (
    get_scanner,
    get_supported_extensions,
    MarkdownScanner,
    PythonScanner,
    JavaScriptScanner,
    SCANNERS
)


class TestScannerRegistry:
    """Test cases for scanner registry."""

    def test_get_scanner_markdown(self):
        """Test getting scanner for markdown files."""
        scanner = get_scanner(Path("README.md"))
        assert scanner is not None
        assert isinstance(scanner, MarkdownScanner)

        scanner = get_scanner(Path("docs/file.markdown"))
        assert scanner is not None
        assert isinstance(scanner, MarkdownScanner)

    def test_get_scanner_python(self):
        """Test getting scanner for Python files."""
        scanner = get_scanner(Path("script.py"))
        assert scanner is not None
        assert isinstance(scanner, PythonScanner)

        scanner = get_scanner(Path("windows_script.pyw"))
        assert scanner is not None
        assert isinstance(scanner, PythonScanner)

    def test_get_scanner_javascript(self):
        """Test getting scanner for JavaScript/TypeScript files."""
        # JavaScript
        scanner = get_scanner(Path("app.js"))
        assert scanner is not None
        assert isinstance(scanner, JavaScriptScanner)

        # JSX
        scanner = get_scanner(Path("component.jsx"))
        assert scanner is not None
        assert isinstance(scanner, JavaScriptScanner)

        # TypeScript
        scanner = get_scanner(Path("types.ts"))
        assert scanner is not None
        assert isinstance(scanner, JavaScriptScanner)

        # TSX
        scanner = get_scanner(Path("component.tsx"))
        assert scanner is not None
        assert isinstance(scanner, JavaScriptScanner)

        # ES modules
        scanner = get_scanner(Path("module.mjs"))
        assert scanner is not None
        assert isinstance(scanner, JavaScriptScanner)

        scanner = get_scanner(Path("module.cjs"))
        assert scanner is not None
        assert isinstance(scanner, JavaScriptScanner)

    def test_get_scanner_unsupported(self):
        """Test getting scanner for unsupported file types."""
        assert get_scanner(Path("file.txt")) is None
        assert get_scanner(Path("image.png")) is None
        assert get_scanner(Path("data.json")) is None
        assert get_scanner(Path("style.css")) is None

    def test_get_scanner_case_insensitive(self):
        """Test that extension matching is case-insensitive."""
        scanner = get_scanner(Path("FILE.MD"))
        assert scanner is not None
        assert isinstance(scanner, MarkdownScanner)

        scanner = get_scanner(Path("SCRIPT.PY"))
        assert scanner is not None
        assert isinstance(scanner, PythonScanner)

        scanner = get_scanner(Path("APP.JS"))
        assert scanner is not None
        assert isinstance(scanner, JavaScriptScanner)

    def test_get_supported_extensions(self):
        """Test getting list of all supported extensions."""
        extensions = get_supported_extensions()

        # Should include all format extensions
        assert '.md' in extensions
        assert '.markdown' in extensions
        assert '.py' in extensions
        assert '.pyw' in extensions
        assert '.js' in extensions
        assert '.jsx' in extensions
        assert '.ts' in extensions
        assert '.tsx' in extensions
        assert '.mjs' in extensions
        assert '.cjs' in extensions

    def test_scanners_dict_complete(self):
        """Test that SCANNERS dict is properly populated."""
        # Should have entries for all supported extensions
        assert '.md' in SCANNERS
        assert '.py' in SCANNERS
        assert '.js' in SCANNERS
        assert '.ts' in SCANNERS

        # All entries should be scanner instances
        for ext, scanner in SCANNERS.items():
            assert hasattr(scanner, 'extract_metadata')
            assert hasattr(scanner, 'supported_extensions')

    def test_scanner_instances_shared(self):
        """Test that same scanner instance is returned for related extensions."""
        md_scanner = get_scanner(Path("file.md"))
        markdown_scanner = get_scanner(Path("file.markdown"))
        # Should be the same instance
        assert md_scanner is markdown_scanner

        py_scanner = get_scanner(Path("file.py"))
        pyw_scanner = get_scanner(Path("file.pyw"))
        # Should be the same instance
        assert py_scanner is pyw_scanner
