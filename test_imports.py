#!/usr/bin/env python3
"""Validation script to test all imports in contextgit.

This script systematically imports all modules to ensure the package
is correctly wired together and all dependencies are satisfied.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_models():
    """Test models module imports."""
    print("Testing models...", end=" ")
    from contextgit.models import Node, Link, Index, Config
    from contextgit.models import NodeType, NodeStatus, RelationType, SyncStatus
    from contextgit.models import HeadingLocation, LineLocation
    print("✓")


def test_infrastructure():
    """Test infrastructure module imports."""
    print("Testing infrastructure...", end=" ")
    from contextgit.infra import FileSystem, YAMLSerializer, OutputFormatter
    print("✓")


def test_domain():
    """Test domain module imports."""
    print("Testing domain...", end=" ")
    from contextgit.domain.checksum import ChecksumCalculator
    from contextgit.domain.id_gen import IDGenerator
    from contextgit.domain.config import ConfigManager
    from contextgit.domain.index import IndexManager
    from contextgit.domain.metadata import MetadataParser, RawMetadata
    from contextgit.domain.location import (
        LocationResolver, SnippetExtractor, MarkdownParser
    )
    from contextgit.domain.linking import LinkingEngine
    print("✓")


def test_handlers():
    """Test handlers module imports."""
    print("Testing handlers...", end=" ")
    from contextgit.handlers import (
        InitHandler, ScanHandler, StatusHandler,
        LinkHandler, ConfirmHandler,
        next_id_command, relevant_command, status_command
    )
    from contextgit.handlers.show_handler import ShowHandler
    from contextgit.handlers.extract_handler import ExtractHandler
    from contextgit.handlers.fmt_handler import FmtHandler
    print("✓")


def test_cli():
    """Test CLI module imports."""
    print("Testing CLI...", end=" ")
    from contextgit.cli import app, console
    from contextgit.cli.commands import (
        init_command, scan_command, status_command,
        show_command, extract_command, link_command,
        confirm_command, next_id_command, relevant_command,
        fmt_command
    )
    print("✓")


def test_exceptions():
    """Test exceptions module."""
    print("Testing exceptions...", end=" ")
    from contextgit.exceptions import (
        ContextGitError, RepoNotFoundError, NodeNotFoundError,
        IndexCorruptedError, InvalidMetadataError
    )
    print("✓")


def test_constants():
    """Test constants module."""
    print("Testing constants...", end=" ")
    from contextgit.constants import (
        CONTEXTGIT_DIR, CONFIG_FILE, INDEX_FILE,
        MAX_FILE_SIZE, MAX_SNIPPET_SIZE, DEFAULT_ID_PADDING
    )
    print("✓")


def main():
    """Run all import tests."""
    print("=" * 60)
    print("contextgit Import Validation")
    print("=" * 60)
    print()

    tests = [
        test_constants,
        test_exceptions,
        test_models,
        test_infrastructure,
        test_domain,
        test_handlers,
        test_cli,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ FAILED")
            print(f"  Error: {e}")
            failed.append((test.__name__, e))

    print()
    print("=" * 60)
    if failed:
        print(f"FAILED: {len(failed)} test(s) failed")
        for test_name, error in failed:
            print(f"  - {test_name}: {error}")
        sys.exit(1)
    else:
        print("SUCCESS: All imports validated!")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
