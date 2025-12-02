"""Unit tests for InitHandler."""

import json
import tempfile
from pathlib import Path
import pytest

from contextgit.handlers.init_handler import InitHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.constants import CONTEXTGIT_DIR, CONFIG_FILE, INDEX_FILE


class TestInitHandler:
    """Tests for InitHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create InitHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return InitHandler(fs, yaml, formatter)

    def test_init_creates_contextgit_directory(self, handler, temp_dir):
        """Test that init creates .contextgit directory."""
        result = handler.handle(directory=temp_dir, format="text")

        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        assert contextgit_dir.exists()
        assert contextgit_dir.is_dir()
        assert "Repository initialized for contextgit" in result

    def test_init_creates_config_file(self, handler, temp_dir):
        """Test that init creates config.yaml with default values."""
        handler.handle(directory=temp_dir, format="text")

        config_path = Path(temp_dir) / CONTEXTGIT_DIR / CONFIG_FILE
        assert config_path.exists()

        # Read and verify config content
        with open(config_path, 'r') as f:
            content = f.read()
            assert 'tag_prefixes:' in content
            assert 'directories:' in content
            assert 'business: BR-' in content

    def test_init_creates_empty_index(self, handler, temp_dir):
        """Test that init creates empty requirements_index.yaml."""
        handler.handle(directory=temp_dir, format="text")

        index_path = Path(temp_dir) / CONTEXTGIT_DIR / INDEX_FILE
        assert index_path.exists()

        # Read and verify index is empty
        with open(index_path, 'r') as f:
            content = f.read()
            assert 'nodes: []' in content
            assert 'links: []' in content

    def test_init_without_directory_uses_current(self, handler, temp_dir, monkeypatch):
        """Test that init uses current directory when no directory specified."""
        # Change to temp directory
        monkeypatch.chdir(temp_dir)

        result = handler.handle(directory=None, format="text")

        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        assert contextgit_dir.exists()
        assert "Repository initialized for contextgit" in result

    def test_init_raises_error_if_already_initialized(self, handler, temp_dir):
        """Test that init raises error if .contextgit already exists."""
        # Initialize once
        handler.handle(directory=temp_dir, format="text")

        # Try to initialize again without --force
        with pytest.raises(FileExistsError) as exc_info:
            handler.handle(directory=temp_dir, force=False, format="text")

        assert "already initialized" in str(exc_info.value)
        assert "Use --force" in str(exc_info.value)

    def test_init_with_force_overwrites_existing(self, handler, temp_dir):
        """Test that init with --force overwrites existing configuration."""
        # Initialize once
        handler.handle(directory=temp_dir, format="text")

        # Modify the config file
        config_path = Path(temp_dir) / CONTEXTGIT_DIR / CONFIG_FILE
        with open(config_path, 'w') as f:
            f.write("# Modified config\n")

        # Initialize again with force
        result = handler.handle(directory=temp_dir, force=True, format="text")

        # Verify config was overwritten
        with open(config_path, 'r') as f:
            content = f.read()
            assert '# Modified config' not in content
            assert 'tag_prefixes:' in content
            assert "Repository initialized for contextgit" in result

    def test_init_json_output_format(self, handler, temp_dir):
        """Test that init supports JSON output format."""
        result = handler.handle(directory=temp_dir, format="json")

        # Parse JSON result
        data = json.loads(result)
        assert data['status'] == 'success'
        assert data['directory'] == str(Path(temp_dir).resolve())
        assert 'Initialized contextgit repository' in data['message']

    def test_init_text_output_format(self, handler, temp_dir):
        """Test that init produces proper text output."""
        result = handler.handle(directory=temp_dir, format="text")

        assert "Created" in result
        assert "config.yaml" in result
        assert "requirements_index.yaml" in result
        assert "Repository initialized for contextgit" in result

    def test_init_creates_nested_directory_if_needed(self, handler, temp_dir):
        """Test that init creates nested directories if they don't exist."""
        nested_dir = Path(temp_dir) / "nested" / "path" / "project"

        result = handler.handle(directory=str(nested_dir), format="text")

        contextgit_dir = nested_dir / CONTEXTGIT_DIR
        assert contextgit_dir.exists()
        assert contextgit_dir.is_dir()
        assert "Repository initialized for contextgit" in result
