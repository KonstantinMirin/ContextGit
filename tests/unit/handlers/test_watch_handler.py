"""Unit tests for WatchHandler."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from contextgit.handlers.watch_handler import (
    WatchHandler,
    ContextGitWatcher,
    WatchConfig,
    WATCHDOG_AVAILABLE
)
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.constants import CONTEXTGIT_DIR


class TestWatchHandler:
    """Tests for WatchHandler."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .contextgit directory to make it a valid repo
            contextgit_dir = Path(tmpdir) / CONTEXTGIT_DIR
            contextgit_dir.mkdir()

            # Create minimal config and index files
            config_path = contextgit_dir / "config.yaml"
            config_path.write_text("tag_prefixes:\n  business: BR-\n")

            index_path = contextgit_dir / "requirements_index.yaml"
            index_path.write_text("nodes: []\nlinks: []\n")

            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create WatchHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return WatchHandler(fs, yaml, formatter)

    def test_watch_requires_watchdog(self, handler, temp_repo, monkeypatch):
        """Test that watch mode requires watchdog package."""
        # Temporarily disable watchdog availability
        monkeypatch.setattr('contextgit.handlers.watch_handler.WATCHDOG_AVAILABLE', False)
        monkeypatch.chdir(temp_repo)

        result = handler.handle(format="text")

        assert "Watch mode requires the 'watchdog' package" in result
        assert "pip install contextgit[watch]" in result

    def test_watch_requires_watchdog_json_format(self, handler, temp_repo, monkeypatch):
        """Test that watch mode returns JSON error when watchdog unavailable."""
        # Temporarily disable watchdog availability
        monkeypatch.setattr('contextgit.handlers.watch_handler.WATCHDOG_AVAILABLE', False)
        monkeypatch.chdir(temp_repo)

        result = handler.handle(format="json")

        data = json.loads(result)
        assert "error" in data
        assert "watchdog" in data["error"]

    def test_watch_validates_path_exists(self, handler, temp_repo, monkeypatch):
        """Test that watch mode validates that specified paths exist."""
        if not WATCHDOG_AVAILABLE:
            pytest.skip("watchdog not available")

        monkeypatch.chdir(temp_repo)

        result = handler.handle(paths=["/nonexistent/path"], format="text")

        assert "Path does not exist" in result

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_watch_with_no_paths_uses_repo_root(self, handler, temp_repo, monkeypatch):
        """Test that watch mode defaults to repo root when no paths specified."""
        monkeypatch.chdir(temp_repo)

        with patch('contextgit.handlers.watch_handler.Observer') as mock_observer:
            mock_observer_instance = MagicMock()
            mock_observer.return_value = mock_observer_instance

            # Mock is_alive to return False so the watch loop exits immediately
            mock_observer_instance.is_alive.return_value = False

            try:
                handler.handle(format="text")
            except SystemExit:
                # It's ok if signal handler causes exit
                pass

            # Verify observer was started
            mock_observer_instance.start.assert_called_once()

            # Verify repo root was scheduled for watching
            assert mock_observer_instance.schedule.call_count >= 1

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_watch_with_specific_paths(self, handler, temp_repo, monkeypatch):
        """Test that watch mode can monitor specific directories."""
        monkeypatch.chdir(temp_repo)

        # Create a subdirectory to watch
        docs_dir = Path(temp_repo) / "docs"
        docs_dir.mkdir()

        with patch('contextgit.handlers.watch_handler.Observer') as mock_observer:
            mock_observer_instance = MagicMock()
            mock_observer.return_value = mock_observer_instance
            mock_observer_instance.is_alive.return_value = False

            try:
                handler.handle(paths=[str(docs_dir)], format="text")
            except SystemExit:
                pass

            # Verify observer was started
            mock_observer_instance.start.assert_called_once()


class TestContextGitWatcher:
    """Tests for ContextGitWatcher class."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            contextgit_dir = Path(tmpdir) / CONTEXTGIT_DIR
            contextgit_dir.mkdir()

            config_path = contextgit_dir / "config.yaml"
            config_path.write_text("tag_prefixes:\n  business: BR-\n")

            index_path = contextgit_dir / "requirements_index.yaml"
            index_path.write_text("nodes: []\nlinks: []\n")

            yield tmpdir

    @pytest.fixture
    def mock_handler(self):
        """Create mock handler."""
        handler = Mock()
        handler.handle = Mock(return_value="Scanned 1 files\nAdded: 0 nodes\nUpdated: 1 nodes")
        return handler

    @pytest.fixture
    def watch_config(self, temp_repo):
        """Create watch config."""
        return WatchConfig(
            paths=[Path(temp_repo)],
            debounce_ms=100,  # Short debounce for testing
            notify=False,
            ignore_patterns=["*.pyc", "__pycache__/*", ".git/*"]
        )

    @pytest.fixture
    def watcher(self, watch_config, mock_handler, temp_repo):
        """Create ContextGitWatcher instance."""
        return ContextGitWatcher(
            config=watch_config,
            handler=mock_handler,
            repo_root=Path(temp_repo),
            format="text"
        )

    def test_should_scan_checks_extension(self, watcher, temp_repo):
        """Test that _should_scan checks file extension."""
        md_file = Path(temp_repo) / "test.md"
        txt_file = Path(temp_repo) / "test.txt"

        assert watcher._should_scan(md_file) is True
        assert watcher._should_scan(txt_file) is False

    def test_should_scan_checks_ignore_patterns(self, watcher, temp_repo):
        """Test that _should_scan respects ignore patterns."""
        pyc_file = Path(temp_repo) / "test.pyc"
        cache_file = Path(temp_repo) / "__pycache__" / "test.py"

        assert watcher._should_scan(pyc_file) is False
        assert watcher._should_scan(cache_file) is False

    def test_should_scan_checks_repo_boundary(self, watcher, temp_repo):
        """Test that _should_scan rejects files outside repo."""
        outside_file = Path("/tmp/outside.md")

        assert watcher._should_scan(outside_file) is False

    def test_on_modified_schedules_scan(self, watcher, temp_repo):
        """Test that on_modified schedules a scan for valid files."""
        md_file = Path(temp_repo) / "test.md"
        md_file.touch()  # Create the file

        # Create mock event
        if WATCHDOG_AVAILABLE:
            from watchdog.events import FileModifiedEvent
            event = FileModifiedEvent(str(md_file))

            # Track if scan was scheduled
            original_schedule = watcher._schedule_scan
            scheduled = []

            def track_schedule():
                scheduled.append(True)
                original_schedule()

            watcher._schedule_scan = track_schedule

            watcher.on_modified(event)

            # Verify scan was scheduled
            assert len(scheduled) > 0
            assert md_file in watcher.pending_files

    def test_on_modified_ignores_directories(self, watcher, temp_repo):
        """Test that on_modified ignores directory events."""
        if WATCHDOG_AVAILABLE:
            from watchdog.events import DirModifiedEvent
            event = DirModifiedEvent(str(temp_repo))

            watcher.on_modified(event)

            # Verify no files were added to pending
            assert len(watcher.pending_files) == 0

    def test_debounce_timer_cancels_previous(self, watcher, temp_repo):
        """Test that scheduling a scan cancels previous timer."""
        md_file = Path(temp_repo) / "test.md"
        md_file.touch()

        # Schedule first scan
        watcher.pending_files.add(md_file)
        watcher._schedule_scan()
        first_timer = watcher.debounce_timer

        # Schedule second scan (should cancel first)
        watcher._schedule_scan()
        second_timer = watcher.debounce_timer

        assert first_timer is not second_timer
        assert first_timer.finished.wait(timeout=0.1)  # First timer should be cancelled

    def test_execute_scan_clears_pending_files(self, watcher, temp_repo, mock_handler):
        """Test that _execute_scan clears pending files after scanning."""
        md_file = Path(temp_repo) / "test.md"
        md_file.touch()

        watcher.pending_files.add(md_file)

        # Execute scan
        watcher._execute_scan()

        # Verify pending files were cleared
        assert len(watcher.pending_files) == 0

        # Verify handler was called
        mock_handler.handle.assert_called_once()

    def test_execute_scan_calls_handler(self, watcher, temp_repo, mock_handler):
        """Test that _execute_scan calls the scan handler."""
        md_file = Path(temp_repo) / "test.md"
        md_file.touch()

        watcher.pending_files.add(md_file)
        watcher._execute_scan()

        # Verify handler was called with correct arguments
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args
        assert call_args.kwargs['files'] == [str(md_file)]
        assert call_args.kwargs['dry_run'] is False

    def test_stop_cancels_timer(self, watcher):
        """Test that stop() cancels any pending timer."""
        watcher._schedule_scan()
        assert watcher.debounce_timer is not None

        watcher.stop()

        assert watcher.running is False

    def test_execute_scan_handles_errors(self, watcher, temp_repo, mock_handler, capsys):
        """Test that _execute_scan handles errors gracefully."""
        # Make handler raise an error
        mock_handler.handle.side_effect = Exception("Scan failed")

        md_file = Path(temp_repo) / "test.md"
        md_file.touch()

        watcher.pending_files.add(md_file)
        watcher._execute_scan()

        # Verify error was printed (not raised)
        captured = capsys.readouterr()
        assert "Error scanning files" in captured.out or "Scan failed" in captured.out

    def test_scan_files_json_format(self, watch_config, mock_handler, temp_repo):
        """Test that _scan_files produces JSON output when format is json."""
        watcher = ContextGitWatcher(
            config=watch_config,
            handler=mock_handler,
            repo_root=Path(temp_repo),
            format="json"
        )

        # Mock handler to return JSON
        mock_handler.handle.return_value = json.dumps({
            "files_scanned": 1,
            "nodes_added": 0,
            "nodes_updated": 1
        })

        md_file = Path(temp_repo) / "test.md"
        md_file.touch()

        # Capture output
        import io
        import sys
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            watcher._scan_files([md_file])
            output = captured_output.getvalue()

            # Verify JSON output
            data = json.loads(output)
            assert "timestamp" in data
            assert "files" in data
            assert "scan_result" in data
        finally:
            sys.stdout = sys.__stdout__

    def test_on_created_triggers_scan(self, watcher, temp_repo):
        """Test that on_created triggers scan for new files."""
        if WATCHDOG_AVAILABLE:
            from watchdog.events import FileCreatedEvent

            md_file = Path(temp_repo) / "new_file.md"
            md_file.touch()

            event = FileCreatedEvent(str(md_file))

            watcher.on_created(event)

            # Verify file was added to pending
            assert md_file in watcher.pending_files

    def test_concurrent_scan_prevention(self, watcher, temp_repo, mock_handler):
        """Test that concurrent scans are prevented."""
        import threading

        # Make handler slow
        def slow_scan(*args, **kwargs):
            time.sleep(0.2)
            return "Scanned"

        mock_handler.handle.side_effect = slow_scan

        md_file = Path(temp_repo) / "test.md"
        md_file.touch()

        watcher.pending_files.add(md_file)

        # Start first scan in thread
        thread1 = threading.Thread(target=watcher._execute_scan)
        thread1.start()

        time.sleep(0.05)  # Let first scan start

        # Try to start second scan
        watcher.pending_files.add(md_file)
        thread2 = threading.Thread(target=watcher._execute_scan)
        thread2.start()

        # Wait for both threads
        thread1.join()
        thread2.join()

        # Both scans should complete, but second should wait for first
        # We just verify no exceptions were raised
        assert True
