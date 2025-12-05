"""Handler for contextgit mcp-server command."""

import sys
import asyncio
import typer
from typing import Optional

from contextgit.exceptions import RepoNotFoundError


class MCPServerHandler:
    """Handler for contextgit mcp-server command.

    Starts an MCP (Model Context Protocol) server that exposes
    contextgit functionality to LLMs for real-time querying.
    """

    def handle(
        self,
        transport: str = "stdio",
        port: int = 8080,
        host: str = "localhost",
        repo_root: Optional[str] = None
    ) -> None:
        """Start MCP server.

        Args:
            transport: Transport type (stdio or http)
            port: Port for HTTP transport
            host: Host for HTTP transport
            repo_root: Optional repository root path

        Raises:
            ImportError: If MCP library is not installed
            RepoNotFoundError: If not in a contextgit repository and repo_root not provided
        """
        try:
            from contextgit.mcp.server import ContextGitMCPServer
        except ImportError:
            raise ImportError(
                "MCP library is not installed. "
                "Install it with: pip install 'contextgit[mcp]'"
            )

        try:
            server = ContextGitMCPServer(repo_root=repo_root)

            if transport == "stdio":
                asyncio.run(server.run_stdio())
            elif transport == "http":
                asyncio.run(server.run_http(host=host, port=port))
            else:
                raise ValueError(f"Unknown transport: {transport}")

        except RepoNotFoundError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Failed to start MCP server: {e}")


def mcp_server_command(
    transport: str = typer.Option(
        "stdio",
        "--transport",
        "-t",
        help="Transport type: stdio (for Claude Code) or http"
    ),
    port: int = typer.Option(
        8080,
        "--port",
        "-p",
        help="Port for HTTP transport (default: 8080)"
    ),
    host: str = typer.Option(
        "localhost",
        "--host",
        help="Host for HTTP transport (default: localhost)"
    ),
    repo_root: Optional[str] = typer.Option(
        None,
        "--repo-root",
        "-r",
        help="Repository root path (optional, will auto-detect if not provided)"
    ),
):
    """Start MCP server for LLM integration.

    The MCP (Model Context Protocol) server allows LLMs like Claude to query
    requirements in real-time through a standardized interface.

    Supports two transport modes:
    - stdio (default): For integration with Claude Code and similar CLIs
    - http: For web-based integrations (experimental)

    The server exposes 5 tools:
    - contextgit_relevant_for_file: Find requirements for a source file
    - contextgit_extract: Get full context for a requirement
    - contextgit_status: Get project health status
    - contextgit_impact_analysis: Analyze change impact
    - contextgit_search: Search requirements by keyword

    And 2 resources:
    - contextgit://index: Full requirements index
    - contextgit://llm-instructions: LLM integration instructions

    Examples:
        # Start with stdio transport (for Claude Code)
        contextgit mcp-server

        # Start with HTTP transport
        contextgit mcp-server --transport http --port 8080

        # Specify custom repository root
        contextgit mcp-server --repo-root /path/to/project
    """
    handler = MCPServerHandler()

    try:
        handler.handle(
            transport=transport,
            port=port,
            host=host,
            repo_root=repo_root
        )
    except ImportError as e:
        typer.echo(f"Error: {e}", err=True)
        typer.echo(
            "\nTo install MCP support, run:\n"
            "  pip install 'contextgit[mcp]'",
            err=True
        )
        raise typer.Exit(code=1)
    except RepoNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\nMCP server stopped.", err=True)
        raise typer.Exit(code=0)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
