"""CLI command for contextgit watch."""

from typing import List, Optional
import typer

from contextgit.handlers.watch_handler import WatchHandler
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter
from contextgit.cli.app import app


@app.command("watch")
def watch_command(
    paths: Optional[List[str]] = typer.Argument(
        None,
        help="Directories to watch (default: repo root)"
    ),
    notify: bool = typer.Option(
        False,
        "--notify",
        help="Enable desktop notifications (not yet implemented)"
    ),
    debounce: int = typer.Option(
        500,
        "--debounce",
        help="Debounce delay in milliseconds"
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text or json"
    ),
):
    """Watch for file changes and auto-scan.

    Monitors directories for file changes and automatically scans modified
    files. This is useful during active development to keep the requirements
    index up-to-date in real-time.

    By default, watches the repository root. You can specify one or more
    directories to watch instead.

    Only files with supported extensions (.md, .py, .js, .ts, etc.) are
    scanned. Common ignore patterns are automatically applied (*.pyc,
    __pycache__, .git, node_modules, etc.).

    Examples:
        # Watch repo root
        contextgit watch

        # Watch specific directories
        contextgit watch docs/ src/

        # Adjust debounce delay (useful for slow systems)
        contextgit watch --debounce 1000

        # JSON output for programmatic consumption
        contextgit watch --format json

    Notes:
        - Requires watchdog package: pip install contextgit[watch]
        - Press Ctrl+C to stop watching
        - Changes are debounced to avoid excessive scanning
    """
    fs = FileSystem()
    yaml = YAMLSerializer()
    formatter = OutputFormatter()
    handler = WatchHandler(fs, yaml, formatter)

    try:
        result = handler.handle(
            paths=paths,
            notify=notify,
            debounce=debounce,
            format=format
        )
        if result:  # Only print if there's an error message
            typer.echo(result)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
