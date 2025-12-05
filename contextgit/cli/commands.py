"""CLI command definitions.

contextgit:
  id: C-102
  type: code
  title: "CLI Command Registry - Central Command Definitions"
  status: active
  upstream: [SR-012]
  tags: [cli, commands, typer]

This module serves as the central registry for all contextgit commands.
All 10 MVP commands are registered here with the Typer app.
"""

from contextgit.cli.app import app

# Import all command functions from handlers
from contextgit.handlers.init_handler import init_command
from contextgit.handlers.scan_handler import scan_command
from contextgit.handlers.status_handler import status_command
from contextgit.handlers.extract_handler import extract_command
from contextgit.handlers.link_handler import link_command
from contextgit.handlers.next_id_handler import next_id_command
from contextgit.handlers.relevant_handler import relevant_command
from contextgit.handlers.impact_handler import impact_command
from contextgit.handlers.mcp_server_handler import mcp_server_command
from contextgit.handlers.validate_handler import validate_command

# Import from CLI-specific modules (these wrap handlers with Typer decorators)
from contextgit.cli.show_command import show_command
from contextgit.cli.fmt_command import fmt_command
from contextgit.cli.confirm_command import confirm_command
from contextgit.cli.hooks_command import hooks_app
from contextgit.cli.watch_command import watch_command

# Register all commands with the Typer app
# Order matches the documentation for consistency

# Core initialization and scanning
app.command(name="init")(init_command)
app.command(name="scan")(scan_command)

# Status and information
app.command(name="status")(status_command)
app.command(name="show")(show_command)
app.command(name="extract")(extract_command)

# Linking and synchronization
app.command(name="link")(link_command)
app.command(name="confirm")(confirm_command)

# Utilities
app.command(name="next-id")(next_id_command)
app.command(name="relevant-for-file")(relevant_command)
app.command(name="fmt")(fmt_command)
app.command(name="impact")(impact_command)
app.command(name="validate")(validate_command)

# Watch mode
app.command(name="watch")(watch_command)

# MCP Server
app.command(name="mcp-server")(mcp_server_command)

# Git Hooks (subcommand group)
app.add_typer(hooks_app, name="hooks")
