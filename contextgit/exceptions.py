"""Custom exceptions for contextgit."""


class ContextGitError(Exception):
    """Base exception for all contextgit errors."""

    exit_code = 1


class RepoNotFoundError(ContextGitError):
    """Raised when not in a contextgit repository."""

    exit_code = 1


class NodeNotFoundError(ContextGitError):
    """Raised when a node ID is not found."""

    exit_code = 3


class InvalidMetadataError(ContextGitError):
    """Raised when metadata is malformed."""

    exit_code = 4


class IndexCorruptedError(ContextGitError):
    """Raised when index file is corrupted."""

    exit_code = 5


class InvalidConfigError(ContextGitError):
    """Raised when config file is malformed."""

    exit_code = 6


class SecurityError(ContextGitError):
    """Raised for security violations (path traversal, etc.)."""

    exit_code = 7


class SelfReferentialError(ContextGitError):
    """Raised when a node references itself in upstream/downstream."""

    exit_code = 8

    def __init__(self, node_id: str, file: str = None, line: int = None):
        """
        Initialize SelfReferentialError.

        Args:
            node_id: The ID of the node that references itself
            file: The file where the self-reference occurs
            line: The line number where the self-reference occurs
        """
        msg = f"True self-reference detected: {node_id} references itself."
        if file:
            msg += f"\nLocation: {file}"
            if line:
                msg += f":{line}"
        msg += "\nNote: Parent-child references within the same file ARE allowed."
        super().__init__(msg)
        self.node_id = node_id
        self.file = file
        self.line = line


class CircularDependencyError(ContextGitError):
    """Raised when a circular dependency is detected across files."""

    exit_code = 9

    def __init__(self, cycle: list[str], message: str = None):
        """
        Initialize CircularDependencyError.

        Args:
            cycle: List of node IDs forming the cycle
            message: Optional custom message
        """
        if message:
            msg = message
        else:
            cycle_str = " -> ".join(cycle)
            msg = f"Circular dependency detected: {cycle_str}"
        super().__init__(msg)
        self.cycle = cycle
