"""Handler for contextgit watch command.

contextgit:
  id: C-114
  type: code
  title: "Watch Handler - File System Monitoring"
  status: active
  upstream: [SR-012]
  tags: [cli, watch-mode, automation, watchdog]

This module implements the WatchHandler, which monitors files for changes
and automatically scans them when modifications are detected.

Key Features:
-------------
1. **File System Watching**: Uses watchdog library to monitor file system events
2. **Debouncing**: Groups rapid file changes to avoid excessive scanning
3. **Selective Scanning**: Only scans files with supported extensions
4. **Ignore Patterns**: Respects common ignore patterns (*.pyc, __pycache__, etc.)
5. **Live Updates**: Displays real-time scan results as files change
6. **Graceful Shutdown**: Handles Ctrl+C cleanly
"""

import json
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Provide dummy classes for type hints
    class FileSystemEventHandler:  # type: ignore
        pass
    class Observer:  # type: ignore
        pass
    class FileSystemEvent:  # type: ignore
        pass

from contextgit.handlers.base import BaseHandler
from contextgit.handlers.scan_handler import ScanHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.scanners import get_scanner, get_supported_extensions


@dataclass
class WatchConfig:
    """Configuration for watch mode."""
    paths: list[Path]
    debounce_ms: int
    notify: bool
    ignore_patterns: list[str]


class ContextGitWatcher(FileSystemEventHandler):
    """File system event handler for contextgit watch mode.

    Monitors file system events and schedules scans for modified files.
    Implements debouncing to avoid excessive scanning of rapidly changing files.
    """

    def __init__(
        self,
        config: WatchConfig,
        handler: BaseHandler,
        repo_root: Path,
        format: str = "text"
    ):
        """Initialize the watcher.

        Args:
            config: Watch configuration
            handler: ScanHandler instance for processing files
            repo_root: Repository root path
            format: Output format (text or json)
        """
        super().__init__()
        self.config = config
        self.handler = handler
        self.repo_root = repo_root
        self.format = format
        self.pending_files: Set[Path] = set()
        self.debounce_timer: Optional[threading.Timer] = None
        self.timer_lock = threading.Lock()
        self.scan_lock = threading.Lock()
        self.running = True

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return

        path = Path(event.src_path)

        if self._should_scan(path):
            with self.timer_lock:
                self.pending_files.add(path)
                self._schedule_scan()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events.

        Args:
            event: File system event from watchdog
        """
        # Treat file creation the same as modification
        self.on_modified(event)

    def _should_scan(self, path: Path) -> bool:
        """Check if file should be scanned.

        Checks:
        1. File has a supported extension
        2. File doesn't match any ignore patterns
        3. File is within the repository

        Args:
            path: File path to check

        Returns:
            True if file should be scanned, False otherwise
        """
        # Check if file has supported extension
        scanner = get_scanner(path)
        if not scanner:
            return False

        # Check ignore patterns
        for pattern in self.config.ignore_patterns:
            if path.match(pattern):
                return False

        # Check if file is within repo
        try:
            path.relative_to(self.repo_root)
        except ValueError:
            # File is outside repo
            return False

        return True

    def _schedule_scan(self) -> None:
        """Schedule a debounced scan.

        Cancels any existing timer and starts a new one. When the timer fires,
        all pending files will be scanned.
        """
        # Cancel existing timer if any
        if self.debounce_timer is not None:
            self.debounce_timer.cancel()

        # Create new timer
        delay_seconds = self.config.debounce_ms / 1000.0
        self.debounce_timer = threading.Timer(delay_seconds, self._execute_scan)
        self.debounce_timer.daemon = True
        self.debounce_timer.start()

    def _execute_scan(self) -> None:
        """Execute scan for all pending files.

        Called when debounce timer fires. Scans all files that have been
        modified since the last scan.
        """
        if not self.running:
            return

        with self.timer_lock:
            files_to_scan = list(self.pending_files)
            self.pending_files.clear()

        if not files_to_scan:
            return

        # Prevent concurrent scans
        with self.scan_lock:
            self._scan_files(files_to_scan)

    def _scan_files(self, files: list[Path]) -> None:
        """Scan a list of files and display results.

        Args:
            files: List of file paths to scan
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        if self.format == "json":
            # JSON format: just output scan results
            try:
                result = self.handler.handle(
                    path=None,
                    recursive=False,
                    files=[str(f) for f in files],
                    dry_run=False,
                    format="json"
                )
                output = {
                    "timestamp": timestamp,
                    "files": [str(f.relative_to(self.repo_root)) for f in files],
                    "scan_result": json.loads(result)
                }
                print(json.dumps(output, indent=2))
            except Exception as e:
                error = {
                    "timestamp": timestamp,
                    "error": str(e),
                    "files": [str(f) for f in files]
                }
                print(json.dumps(error, indent=2))
        else:
            # Text format: human-readable output
            try:
                # Display modified files
                for file in files:
                    rel_path = file.relative_to(self.repo_root)
                    print(f"[{timestamp}] Modified: {rel_path}")

                # Run scan
                result = self.handler.handle(
                    path=None,
                    recursive=False,
                    files=[str(f) for f in files],
                    dry_run=False,
                    format="text"
                )

                # Parse and display results
                lines = result.split('\n')
                for line in lines:
                    if line.strip():
                        print(f"           {line}")

                print()  # Empty line between scans

            except Exception as e:
                print(f"[{timestamp}] Error scanning files: {e}")
                print()

    def stop(self) -> None:
        """Stop the watcher gracefully."""
        self.running = False
        with self.timer_lock:
            if self.debounce_timer is not None:
                self.debounce_timer.cancel()
                self.debounce_timer = None


class WatchHandler(BaseHandler):
    """Handler for contextgit watch command.

    Monitors directories for file changes and automatically scans modified files.
    Provides real-time updates as requirements and code files are modified.
    """

    def handle(
        self,
        paths: list[str] | None = None,
        notify: bool = False,
        debounce: int = 500,
        format: str = "text"
    ) -> str:
        """Watch directories for changes and auto-scan.

        Args:
            paths: Directories to watch (default: repo root)
            notify: Enable desktop notifications (not yet implemented)
            debounce: Debounce delay in milliseconds
            format: Output format (text or json)

        Returns:
            Status message (only on error, otherwise runs until interrupted)

        Raises:
            ImportError: If watchdog is not installed
            RepoNotFoundError: If not in a contextgit repository
        """
        # Check if watchdog is available
        if not WATCHDOG_AVAILABLE:
            error_msg = (
                "Watch mode requires the 'watchdog' package.\n"
                "Install it with: pip install contextgit[watch]"
            )
            if format == "json":
                return json.dumps({"error": error_msg})
            return error_msg

        # Find repo root
        repo_root = Path(self.find_repo_root())

        # Determine watch paths
        watch_paths = []
        if paths:
            for path_str in paths:
                path = Path(path_str).resolve()
                # Validate path exists
                if not path.exists():
                    error_msg = f"Path does not exist: {path}"
                    if format == "json":
                        return json.dumps({"error": error_msg})
                    return error_msg
                watch_paths.append(path)
        else:
            # Default to repo root
            watch_paths = [repo_root]

        # Build ignore patterns
        ignore_patterns = [
            "*.pyc",
            "*.pyo",
            "__pycache__/*",
            ".git/*",
            ".contextgit/*",
            "node_modules/*",
            ".venv/*",
            "venv/*",
            "*.egg-info/*",
            ".pytest_cache/*",
            "__pycache__",
            "*.swp",
            "*.swo",
            "*~",
        ]

        # Create watch config
        config = WatchConfig(
            paths=watch_paths,
            debounce_ms=debounce,
            notify=notify,
            ignore_patterns=ignore_patterns
        )

        # Create scan handler
        scan_handler = ScanHandler(self.fs, self.yaml, self.formatter)

        # Create watcher
        watcher = ContextGitWatcher(config, scan_handler, repo_root, format)

        # Create observer
        observer = Observer()
        for watch_path in watch_paths:
            observer.schedule(watcher, str(watch_path), recursive=True)

        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            if format == "text":
                print("\nStopping watch mode...")
            watcher.stop()
            observer.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start observer
        observer.start()

        # Display startup message
        if format == "text":
            rel_paths = [str(p.relative_to(repo_root) if p != repo_root else ".")
                        for p in watch_paths]
            print(f"🔍 Watching: {', '.join(rel_paths)}")
            print("Press Ctrl+C to stop\n")
        else:
            startup = {
                "status": "watching",
                "paths": [str(p) for p in watch_paths],
                "debounce_ms": debounce
            }
            print(json.dumps(startup))

        # Keep running until interrupted
        try:
            while observer.is_alive():
                observer.join(1)
        except KeyboardInterrupt:
            if format == "text":
                print("\nStopping watch mode...")
            watcher.stop()
            observer.stop()

        observer.join()
        return ""
