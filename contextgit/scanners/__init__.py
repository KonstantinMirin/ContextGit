"""Scanner registry for multi-format file support.

This module provides a registry of file scanners and a convenience function
to get the appropriate scanner for a given file path.
"""

from pathlib import Path
from typing import Optional, Dict

from contextgit.scanners.base import FileScanner
from contextgit.scanners.markdown import MarkdownScanner
from contextgit.scanners.python import PythonScanner
from contextgit.scanners.javascript import JavaScriptScanner


# Initialize scanners
_markdown_scanner = MarkdownScanner()
_python_scanner = PythonScanner()
_javascript_scanner = JavaScriptScanner()

# Build scanner registry mapping extensions to scanners
SCANNERS: Dict[str, FileScanner] = {}

for scanner in [_markdown_scanner, _python_scanner, _javascript_scanner]:
    for ext in scanner.supported_extensions:
        SCANNERS[ext.lower()] = scanner


def get_scanner(file_path: Path) -> Optional[FileScanner]:
    """Get the appropriate scanner for a file path.

    Args:
        file_path: Path to file

    Returns:
        FileScanner instance if file type is supported, None otherwise

    Example:
        >>> scanner = get_scanner(Path('README.md'))
        >>> if scanner:
        ...     metadata = scanner.extract_metadata(Path('README.md'))
    """
    return SCANNERS.get(file_path.suffix.lower())


def get_supported_extensions() -> list[str]:
    """Get list of all supported file extensions.

    Returns:
        List of supported extensions (e.g., ['.md', '.py', '.js'])
    """
    return list(SCANNERS.keys())


__all__ = [
    'FileScanner',
    'MarkdownScanner',
    'PythonScanner',
    'JavaScriptScanner',
    'get_scanner',
    'get_supported_extensions',
    'SCANNERS',
]
