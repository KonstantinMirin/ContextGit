"""Integration tests for multi-format file scanning.

This test demonstrates scanning multiple file formats (Markdown, Python, JavaScript)
in a single repository and verifying that nodes and links are created correctly.
"""

import os
import tempfile
from pathlib import Path

from contextgit.handlers.init_handler import InitHandler
from contextgit.handlers.scan_handler import ScanHandler
from contextgit.domain.index.manager import IndexManager
from contextgit.infra.filesystem import FileSystem
from contextgit.infra.yaml_io import YAMLSerializer
from contextgit.infra.output import OutputFormatter


class TestMultiFormatScanning:
    """Integration tests for scanning multiple file formats."""

    def test_scan_markdown_python_javascript(self):
        """Test scanning a repo with Markdown, Python, and JavaScript files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Setup
            fs = FileSystem()
            yaml = YAMLSerializer()
            formatter = OutputFormatter()

            # Initialize repo
            init_handler = InitHandler(fs, yaml, formatter)
            init_handler.handle()

            # Create test files in different formats
            # Markdown file
            Path("requirements.md").write_text("""---
contextgit:
  id: BR-001
  type: business
  title: User Authentication
  status: active
---

# User Authentication

Users should be able to log in.
""")

            # Python file
            Path("auth.py").write_text('''"""
Authentication module.

contextgit:
  id: C-001
  type: code
  title: Python Auth Module
  upstream: [BR-001]
  status: active
"""

def authenticate(username, password):
    """Authenticate a user."""
    return True
''')

            # JavaScript file
            Path("auth.js").write_text("""/**
 * @contextgit
 * id: C-002
 * type: code
 * title: JavaScript Auth Module
 * upstream: [BR-001]
 * status: active
 */

function authenticate(username, password) {
    return true;
}
""")

            # TypeScript file
            Path("types.ts").write_text("""/**
 * @contextgit
 * id: C-003
 * type: code
 * title: TypeScript Type Definitions
 * upstream: [BR-001]
 */

interface User {
    username: string;
    password: string;
}
""")

            # Scan the repository
            scan_handler = ScanHandler(fs, yaml, formatter)
            result = scan_handler.handle(recursive=True)

            # Verify scan results
            assert "4 nodes" in result or "Added: 4" in result

            # Load index and verify
            index_mgr = IndexManager(fs, yaml, tmpdir)
            index = index_mgr.load_index()

            # Check nodes were created
            assert "BR-001" in index.nodes
            assert "C-001" in index.nodes
            assert "C-002" in index.nodes
            assert "C-003" in index.nodes

            # Verify node details
            br_node = index.nodes["BR-001"]
            assert br_node.type.value == "business"
            assert br_node.title == "User Authentication"
            assert br_node.file == "requirements.md"

            py_node = index.nodes["C-001"]
            assert py_node.type.value == "code"
            assert py_node.title == "Python Auth Module"
            assert py_node.file == "auth.py"

            js_node = index.nodes["C-002"]
            assert js_node.type.value == "code"
            assert js_node.title == "JavaScript Auth Module"
            assert js_node.file == "auth.js"

            ts_node = index.nodes["C-003"]
            assert ts_node.type.value == "code"
            assert ts_node.title == "TypeScript Type Definitions"
            assert ts_node.file == "types.ts"

            # Verify links were created
            upstream_links = [
                link for link in index.links
                if link.from_id == "BR-001"
            ]
            assert len(upstream_links) == 3

            # Verify link targets
            link_targets = {link.to_id for link in upstream_links}
            assert "C-001" in link_targets
            assert "C-002" in link_targets
            assert "C-003" in link_targets

    def test_mixed_format_directory(self):
        """Test scanning directory with mixed file types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            fs = FileSystem()
            yaml = YAMLSerializer()
            formatter = OutputFormatter()

            # Initialize
            init_handler = InitHandler(fs, yaml, formatter)
            init_handler.handle()

            # Create subdirectory structure
            Path("src").mkdir()
            Path("tests").mkdir()

            # Create files
            Path("README.md").write_text("""---
contextgit:
  id: BR-001
  type: business
  title: API Service
---
""")

            Path("src/service.py").write_text('''"""
contextgit:
  id: C-001
  type: code
  title: Service Implementation
  upstream: [BR-001]
"""
''')

            Path("src/client.js").write_text("""/**
 * @contextgit
 * id: C-002
 * type: code
 * title: Client Implementation
 * upstream: [BR-001]
 */
""")

            Path("tests/test_service.py").write_text('''"""
contextgit:
  id: T-001
  type: test
  title: Service Tests
  upstream: [C-001]
"""
''')

            # Scan recursively
            scan_handler = ScanHandler(fs, yaml, formatter)
            scan_handler.handle(recursive=True)

            # Verify all files were scanned
            index_mgr = IndexManager(fs, yaml, tmpdir)
            index = index_mgr.load_index()

            assert len(index.nodes) == 4
            assert "BR-001" in index.nodes
            assert "C-001" in index.nodes
            assert "C-002" in index.nodes
            assert "T-001" in index.nodes

            # Verify file paths
            assert index.nodes["BR-001"].file == "README.md"
            assert index.nodes["C-001"].file == "src/service.py"
            assert index.nodes["C-002"].file == "src/client.js"
            assert index.nodes["T-001"].file == "tests/test_service.py"
