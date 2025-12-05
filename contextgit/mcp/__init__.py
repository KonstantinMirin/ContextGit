"""MCP server module for contextgit.

This module provides Model Context Protocol server functionality,
allowing LLMs to query requirements in real-time.
"""

__all__ = ["ContextGitMCPServer", "main"]

from contextgit.mcp.server import ContextGitMCPServer, main
