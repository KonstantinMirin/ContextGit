"""Unit tests for HooksHandler."""

import json
import tempfile
import os
from pathlib import Path
import pytest

from contextgit.handlers.hooks_handler import HooksHandler, CONTEXTGIT_HOOK_MARKER
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.exceptions import RepoNotFoundError
from contextgit.constants import CONTEXTGIT_DIR


class TestHooksHandler:
    """Tests for HooksHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def handler(self):
        """Create HooksHandler instance."""
        fs = FileSystem()
        yaml = YAMLSerializer()
        formatter = OutputFormatter()
        return HooksHandler(fs, yaml, formatter)

    @pytest.fixture
    def initialized_git_repo(self, temp_dir):
        """Create an initialized git repository with contextgit."""
        # Create .git directory
        git_dir = Path(temp_dir) / '.git'
        git_dir.mkdir(parents=True, exist_ok=True)

        # Create hooks directory
        hooks_dir = git_dir / 'hooks'
        hooks_dir.mkdir(exist_ok=True)

        # Create .contextgit directory
        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        contextgit_dir.mkdir(parents=True, exist_ok=True)

        # Create config
        config_path = contextgit_dir / "config.yaml"
        config_path.write_text("tag_prefixes:\n  business: BR-\n")

        return temp_dir

    def test_install_default_hooks_text_format(self, handler, initialized_git_repo, monkeypatch):
        """Test installing default hooks in text format."""
        monkeypatch.chdir(initialized_git_repo)

        result = handler.install(format="text")

        # Check output
        assert "✅ Installed hooks:" in result
        assert "pre-commit" in result
        assert "post-merge" in result
        assert "pre-push" not in result  # Not installed by default

        # Verify files exist and are executable
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'

        pre_commit = hooks_dir / 'pre-commit'
        assert pre_commit.exists()
        assert os.access(str(pre_commit), os.X_OK)
        assert CONTEXTGIT_HOOK_MARKER in pre_commit.read_text()

        post_merge = hooks_dir / 'post-merge'
        assert post_merge.exists()
        assert os.access(str(post_merge), os.X_OK)
        assert CONTEXTGIT_HOOK_MARKER in post_merge.read_text()

        # pre-push should not exist
        pre_push = hooks_dir / 'pre-push'
        assert not pre_push.exists()

    def test_install_all_hooks_including_pre_push(self, handler, initialized_git_repo, monkeypatch):
        """Test installing all hooks including pre-push."""
        monkeypatch.chdir(initialized_git_repo)

        result = handler.install(
            pre_commit=True,
            post_merge=True,
            pre_push=True,
            format="text"
        )

        # Verify all three hooks exist
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'

        for hook_name in ['pre-commit', 'post-merge', 'pre-push']:
            hook_path = hooks_dir / hook_name
            assert hook_path.exists()
            assert os.access(str(hook_path), os.X_OK)
            assert CONTEXTGIT_HOOK_MARKER in hook_path.read_text()

    def test_install_only_pre_commit_hook(self, handler, initialized_git_repo, monkeypatch):
        """Test installing only pre-commit hook."""
        monkeypatch.chdir(initialized_git_repo)

        result = handler.install(
            pre_commit=True,
            post_merge=False,
            pre_push=False,
            format="text"
        )

        # Verify only pre-commit exists
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'

        pre_commit = hooks_dir / 'pre-commit'
        assert pre_commit.exists()

        post_merge = hooks_dir / 'post-merge'
        assert not post_merge.exists()

        pre_push = hooks_dir / 'pre-push'
        assert not pre_push.exists()

    def test_install_hooks_json_format(self, handler, initialized_git_repo, monkeypatch):
        """Test installing hooks with JSON output."""
        monkeypatch.chdir(initialized_git_repo)

        result = handler.install(format="json")
        data = json.loads(result)

        # Check structure
        assert "installed" in data
        assert "updated" in data
        assert "skipped" in data
        assert "hooks_dir" in data

        # Check installed hooks
        assert "pre-commit" in data["installed"]
        assert "post-merge" in data["installed"]

    def test_install_is_idempotent(self, handler, initialized_git_repo, monkeypatch):
        """Test that installing hooks multiple times is idempotent."""
        monkeypatch.chdir(initialized_git_repo)

        # Install first time
        result1 = handler.install(format="text")
        assert "✅ Installed hooks:" in result1

        # Install second time - should update
        result2 = handler.install(format="text")
        assert "🔄 Updated hooks:" in result2
        assert "pre-commit" in result2
        assert "post-merge" in result2

        # Verify hooks still exist and are executable
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'

        for hook_name in ['pre-commit', 'post-merge']:
            hook_path = hooks_dir / hook_name
            assert hook_path.exists()
            assert os.access(str(hook_path), os.X_OK)

    def test_install_skips_custom_hooks(self, handler, initialized_git_repo, monkeypatch):
        """Test that installation skips existing custom (non-contextgit) hooks."""
        monkeypatch.chdir(initialized_git_repo)

        # Create custom pre-commit hook (without contextgit marker)
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'
        custom_hook = hooks_dir / 'pre-commit'
        custom_hook.write_text("#!/bin/bash\n# My custom hook\necho 'custom'\n")

        # Try to install
        result = handler.install(format="text")

        # Should skip the custom hook
        assert "⚠️  Skipped hooks" in result
        assert "pre-commit" in result

        # Custom hook should be unchanged
        assert "# My custom hook" in custom_hook.read_text()
        assert CONTEXTGIT_HOOK_MARKER not in custom_hook.read_text()

        # post-merge should still be installed
        post_merge = hooks_dir / 'post-merge'
        assert post_merge.exists()
        assert CONTEXTGIT_HOOK_MARKER in post_merge.read_text()

    def test_install_with_fail_on_stale_hint(self, handler, initialized_git_repo, monkeypatch):
        """Test that fail_on_stale option shows environment variable hint."""
        monkeypatch.chdir(initialized_git_repo)

        result = handler.install(fail_on_stale=True, format="text")

        # Check for hint in output
        assert "CONTEXTGIT_FAIL_ON_STALE=1" in result

    def test_uninstall_removes_contextgit_hooks(self, handler, initialized_git_repo, monkeypatch):
        """Test uninstalling contextgit hooks."""
        monkeypatch.chdir(initialized_git_repo)

        # Install hooks first
        handler.install(format="text")

        # Verify hooks exist
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'
        assert (hooks_dir / 'pre-commit').exists()
        assert (hooks_dir / 'post-merge').exists()

        # Uninstall
        result = handler.uninstall(format="text")

        # Check output
        assert "✅ Removed hooks:" in result
        assert "pre-commit" in result
        assert "post-merge" in result

        # Verify hooks are removed
        assert not (hooks_dir / 'pre-commit').exists()
        assert not (hooks_dir / 'post-merge').exists()

    def test_uninstall_preserves_custom_hooks(self, handler, initialized_git_repo, monkeypatch):
        """Test that uninstall preserves custom hooks."""
        monkeypatch.chdir(initialized_git_repo)

        # Create custom pre-commit hook
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'
        custom_hook = hooks_dir / 'pre-commit'
        custom_hook.write_text("#!/bin/bash\n# My custom hook\necho 'custom'\n")

        # Install post-merge (contextgit hook)
        handler.install(pre_commit=False, post_merge=True, format="text")

        # Uninstall
        result = handler.uninstall(format="text")

        # Custom pre-commit should still exist
        assert custom_hook.exists()
        assert "# My custom hook" in custom_hook.read_text()

        # Contextgit post-merge should be removed
        assert not (hooks_dir / 'post-merge').exists()

    def test_uninstall_with_no_hooks_installed(self, handler, initialized_git_repo, monkeypatch):
        """Test uninstalling when no hooks are installed."""
        monkeypatch.chdir(initialized_git_repo)

        result = handler.uninstall(format="text")

        assert "ℹ️  No contextgit hooks found to remove" in result

    def test_uninstall_json_format(self, handler, initialized_git_repo, monkeypatch):
        """Test uninstalling with JSON output."""
        monkeypatch.chdir(initialized_git_repo)

        # Install first
        handler.install(format="text")

        # Uninstall with JSON
        result = handler.uninstall(format="json")
        data = json.loads(result)

        assert "removed" in data
        assert "hooks_dir" in data
        assert "pre-commit" in data["removed"]
        assert "post-merge" in data["removed"]

    def test_status_shows_installed_hooks(self, handler, initialized_git_repo, monkeypatch):
        """Test status shows installed hooks."""
        monkeypatch.chdir(initialized_git_repo)

        # Install hooks
        handler.install(format="text")

        # Check status
        result = handler.status(format="text")

        assert "Git hooks status:" in result
        assert "pre-commit: ✅ (contextgit)" in result
        assert "post-merge: ✅ (contextgit)" in result
        assert "pre-push: ❌ not installed" in result

    def test_status_distinguishes_custom_hooks(self, handler, initialized_git_repo, monkeypatch):
        """Test status distinguishes between contextgit and custom hooks."""
        monkeypatch.chdir(initialized_git_repo)

        # Create custom pre-commit
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'
        custom_hook = hooks_dir / 'pre-commit'
        custom_hook.write_text("#!/bin/bash\necho 'custom'\n")
        custom_hook.chmod(0o755)

        # Install post-merge (contextgit)
        handler.install(pre_commit=False, post_merge=True, format="text")

        # Check status
        result = handler.status(format="text")

        assert "pre-commit: ✅ (custom)" in result
        assert "post-merge: ✅ (contextgit)" in result

    def test_status_warns_about_non_executable_hooks(self, handler, initialized_git_repo, monkeypatch):
        """Test status warns about non-executable hooks."""
        monkeypatch.chdir(initialized_git_repo)

        # Install hooks
        handler.install(format="text")

        # Remove execute permission from pre-commit
        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'
        pre_commit = hooks_dir / 'pre-commit'
        pre_commit.chmod(0o644)  # Remove execute permission

        # Check status
        result = handler.status(format="text")

        assert "⚠️  (not executable)" in result

    def test_status_json_format(self, handler, initialized_git_repo, monkeypatch):
        """Test status with JSON output."""
        monkeypatch.chdir(initialized_git_repo)

        # Install hooks
        handler.install(format="text")

        # Check status
        result = handler.status(format="json")
        data = json.loads(result)

        assert "hooks" in data
        assert "hooks_dir" in data

        assert data["hooks"]["pre-commit"]["installed"] is True
        assert data["hooks"]["pre-commit"]["is_contextgit"] is True
        assert data["hooks"]["pre-commit"]["is_executable"] is True

        assert data["hooks"]["pre-push"]["installed"] is False

    def test_install_raises_error_when_not_in_repo(self, handler, temp_dir, monkeypatch):
        """Test that install raises RepoNotFoundError when not in a contextgit repo."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(RepoNotFoundError):
            handler.install(format="text")

    def test_install_raises_error_when_not_git_repo(self, handler, temp_dir, monkeypatch):
        """Test that install returns error when not in a git repo."""
        monkeypatch.chdir(temp_dir)

        # Create .contextgit but not .git
        contextgit_dir = Path(temp_dir) / CONTEXTGIT_DIR
        contextgit_dir.mkdir(parents=True, exist_ok=True)
        config_path = contextgit_dir / "config.yaml"
        config_path.write_text("tag_prefixes:\n  business: BR-\n")

        result = handler.install(format="text")

        assert "Error: Not a git repository" in result

    def test_uninstall_raises_error_when_not_in_repo(self, handler, temp_dir, monkeypatch):
        """Test that uninstall raises RepoNotFoundError when not in a contextgit repo."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(RepoNotFoundError):
            handler.uninstall(format="text")

    def test_status_raises_error_when_not_in_repo(self, handler, temp_dir, monkeypatch):
        """Test that status raises RepoNotFoundError when not in a contextgit repo."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(RepoNotFoundError):
            handler.status(format="text")

    def test_hooks_contain_correct_shebang(self, handler, initialized_git_repo, monkeypatch):
        """Test that installed hooks have correct shebang."""
        monkeypatch.chdir(initialized_git_repo)

        handler.install(format="text")

        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'

        for hook_name in ['pre-commit', 'post-merge']:
            hook_path = hooks_dir / hook_name
            content = hook_path.read_text()
            assert content.startswith("#!/bin/bash")

    def test_hooks_contain_contextgit_commands(self, handler, initialized_git_repo, monkeypatch):
        """Test that installed hooks contain contextgit commands."""
        monkeypatch.chdir(initialized_git_repo)

        handler.install(format="text")

        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'

        # pre-commit should scan changed files
        pre_commit = hooks_dir / 'pre-commit'
        content = pre_commit.read_text()
        assert "contextgit scan" in content
        assert "contextgit status --stale" in content

        # post-merge should scan recursively
        post_merge = hooks_dir / 'post-merge'
        content = post_merge.read_text()
        assert "contextgit scan --recursive" in content

    def test_hook_scripts_handle_errors_gracefully(self, handler, initialized_git_repo, monkeypatch):
        """Test that hook scripts handle errors gracefully."""
        monkeypatch.chdir(initialized_git_repo)

        handler.install(format="text")

        hooks_dir = Path(initialized_git_repo) / '.git' / 'hooks'

        # Check that hooks use proper error handling
        pre_commit = hooks_dir / 'pre-commit'
        content = pre_commit.read_text()

        # Should suppress errors from scan (2>/dev/null)
        assert "2>/dev/null" in content

        # Should exit 0 at the end (success by default)
        assert "exit 0" in content

    def test_install_handles_git_worktree(self, handler, initialized_git_repo, monkeypatch):
        """Test that install works with git worktrees."""
        monkeypatch.chdir(initialized_git_repo)

        # Simulate worktree by making .git a file pointing to real git dir
        git_dir = Path(initialized_git_repo) / '.git'
        actual_git_dir = Path(initialized_git_repo) / '.git-actual'
        actual_git_dir.mkdir()
        (actual_git_dir / 'hooks').mkdir()

        # Create .git file
        git_dir.rename(git_dir.with_suffix('.bak'))
        git_dir.write_text(f"gitdir: {actual_git_dir}")

        # Install should work
        result = handler.install(format="text")

        # Hooks should be in actual git dir
        assert (actual_git_dir / 'hooks' / 'pre-commit').exists()
