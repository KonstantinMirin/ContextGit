"""Examples of contextgit metadata in Python files.

This file demonstrates the two supported formats for embedding
contextgit metadata in Python source files.
"""

# Example 1: Module docstring with contextgit metadata
# This format is recommended for module-level requirements

"""
This is the module docstring.

contextgit:
  id: C-015
  type: code
  title: Script Generation Module
  upstream: [SR-012]
  status: active
  tags: [generation, automation]
  llm_generated: false

This module provides script generation functionality.
"""


# Example 2: Comment block format
# This format is useful for function or class-level requirements

# contextgit:
#   id: C-016
#   type: code
#   title: Data Validation Function
#   upstream: [SR-013]
#   status: active
#   tags: [validation, input]

def validate_data(data):
    """Validate input data.

    Args:
        data: Data to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return isinstance(data, dict)


# Example 3: Multiple metadata blocks in one file
# You can have multiple contextgit blocks for different components

# contextgit:
#   id: C-017
#   type: code
#   title: Data Processor Class
#   upstream: [SR-014]
#   downstream: [T-010]

class DataProcessor:
    """Process and transform data."""

    def process(self, data):
        """Process the data."""
        return data


# Example 4: Using 'auto' ID generation
# Set id to 'auto' and contextgit will generate a sequential ID

# contextgit:
#   id: auto
#   type: code
#   title: Helper Function
#   status: draft

def helper_function():
    """A helper function."""
    pass


# Example 5: Minimal required fields
# Only id, type, and title are required

# contextgit:
#   id: C-018
#   type: code
#   title: Simple Function

def simple_function():
    """A simple function with minimal metadata."""
    return True
