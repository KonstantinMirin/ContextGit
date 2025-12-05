"""Base scanner interface for multi-format file support.

This module defines the abstract FileScanner interface and ExtractedMetadata
dataclass used by all file format scanners.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class ExtractedMetadata:
    """Metadata extracted from a file by a scanner.

    This is a scanner-layer data structure that gets converted to RawMetadata
    by the ScanHandler for further processing.
    """

    id: Optional[str]
    type: str
    title: str
    status: str = "active"
    upstream: List[str] = field(default_factory=list)
    downstream: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    llm_generated: bool = False
    line_number: int = 0  # Line where metadata block starts
    raw_content: str = ""  # The raw content block (for snippet extraction)


class FileScanner(ABC):
    """Abstract base class for file format scanners.

    Each scanner is responsible for:
    1. Declaring which file extensions it supports
    2. Extracting contextgit metadata from files in those formats
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of file extensions this scanner supports.

        Extensions should include the leading dot (e.g., ['.py', '.pyw'])
        """
        pass

    @abstractmethod
    def extract_metadata(self, file_path: Path) -> List[ExtractedMetadata]:
        """Extract all contextgit metadata blocks from a file.

        Args:
            file_path: Path to file to scan

        Returns:
            List of extracted metadata blocks (may be empty)

        Raises:
            InvalidMetadataError: If metadata is malformed
            FileNotFoundError: If file doesn't exist
        """
        pass
