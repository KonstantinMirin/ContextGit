"""CLI commands for git hooks management."""

import typer

from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.handlers.hooks_handler import HooksHandler


# Create a sub-application for hooks commands
hooks_app = typer.Typer(
    name="hooks",
    help="Git hooks management for contextgit integration"
)


@hooks_app.command("install")
def hooks_install(
    pre_commit: bool = typer.Option(
        True,
        "--pre-commit/--no-pre-commit",
        help="Install pre-commit hook (scans changed files)"
    ),
    post_merge: bool = typer.Option(
        True,
        "--post-merge/--no-post-merge",
        help="Install post-merge hook (scans after merge)"
    ),
    pre_push: bool = typer.Option(
        False,
        "--pre-push/--no-pre-push",
        help="Install pre-push hook (checks before push)"
    ),
    fail_on_stale: bool = typer.Option(
        False,
        "--fail-on-stale",
        help="Show hint to enable fail-on-stale mode (requires CONTEXTGIT_FAIL_ON_STALE=1 env var)"
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text or json"
    ),
):
    """Install git hooks for automatic contextgit integration.

    Installs git hooks that automatically run contextgit scan when files change.
    Hooks are idempotent and can be safely re-run to update.

    Available hooks:
    - pre-commit: Scans changed files before commit
    - post-merge: Scans repository after merges
    - pre-push: Checks for stale links before push (optional)

    To enable fail-on-stale mode (blocks commits/pushes with stale links):
    Set environment variable: export CONTEXTGIT_FAIL_ON_STALE=1

    Examples:
        # Install default hooks (pre-commit and post-merge)
        contextgit hooks install

        # Install all hooks including pre-push
        contextgit hooks install --pre-push

        # Install only pre-commit hook
        contextgit hooks install --no-post-merge

        # Get JSON output
        contextgit hooks install --format json
    """
    fs = FileSystem()
    yaml = YAMLSerializer()
    formatter = OutputFormatter()
    handler = HooksHandler(fs, yaml, formatter)

    try:
        result = handler.install(
            pre_commit=pre_commit,
            post_merge=post_merge,
            pre_push=pre_push,
            fail_on_stale=fail_on_stale,
            format=format
        )
        typer.echo(result)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@hooks_app.command("uninstall")
def hooks_uninstall(
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text or json"
    ),
):
    """Remove contextgit git hooks.

    Only removes hooks that were created by contextgit. Custom user hooks
    are preserved.

    Examples:
        # Remove all contextgit hooks
        contextgit hooks uninstall

        # Get JSON output
        contextgit hooks uninstall --format json
    """
    fs = FileSystem()
    yaml = YAMLSerializer()
    formatter = OutputFormatter()
    handler = HooksHandler(fs, yaml, formatter)

    try:
        result = handler.uninstall(format=format)
        typer.echo(result)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@hooks_app.command("status")
def hooks_status(
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text or json"
    ),
):
    """Show installed hooks status.

    Displays which hooks are installed, whether they are contextgit hooks
    or custom hooks, and whether they are executable.

    Examples:
        # Show hooks status
        contextgit hooks status

        # Get JSON output
        contextgit hooks status --format json
    """
    fs = FileSystem()
    yaml = YAMLSerializer()
    formatter = OutputFormatter()
    handler = HooksHandler(fs, yaml, formatter)

    try:
        result = handler.status(format=format)
        typer.echo(result)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
