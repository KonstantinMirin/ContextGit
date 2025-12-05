"""Tests for JavaScript/TypeScript file scanner."""

import pytest
from pathlib import Path
from contextgit.scanners.javascript import JavaScriptScanner
from contextgit.scanners.base import ExtractedMetadata
from contextgit.exceptions import InvalidMetadataError


class TestJavaScriptScanner:
    """Test cases for JavaScriptScanner."""

    def test_supported_extensions(self):
        """Test that scanner reports correct extensions."""
        scanner = JavaScriptScanner()
        expected = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']
        assert scanner.supported_extensions == expected

    def test_parse_jsdoc_block(self, tmp_path):
        """Test parsing JSDoc comment block."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""/**
 * @contextgit
 * id: C-017
 * type: code
 * title: Frontend Auth
 * upstream: [SR-008]
 * status: active
 */

function authenticate(user) {
    return true;
}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "C-017"
        assert metadata.type == "code"
        assert metadata.title == "Frontend Auth"
        assert metadata.upstream == ["SR-008"]
        assert metadata.status == "active"

    def test_parse_typescript_jsdoc(self, tmp_path):
        """Test parsing TypeScript file with JSDoc."""
        file_path = tmp_path / "test.ts"
        file_path.write_text("""/**
 * @contextgit
 * id: C-018
 * type: code
 * title: Type Definitions
 * tags: [types, interfaces]
 */

interface User {
    id: string;
    name: string;
}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "C-018"
        assert metadata.type == "code"
        assert metadata.title == "Type Definitions"
        assert metadata.tags == ["types", "interfaces"]

    def test_parse_multiple_jsdoc_blocks(self, tmp_path):
        """Test parsing multiple JSDoc blocks in one file."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""/**
 * @contextgit
 * id: C-001
 * type: code
 * title: First Function
 */
function first() {}

/**
 * @contextgit
 * id: C-002
 * type: code
 * title: Second Function
 * upstream: [C-001]
 */
function second() {}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 2
        assert results[0].id == "C-001"
        assert results[1].id == "C-002"
        assert results[1].upstream == ["C-001"]

    def test_jsdoc_without_contextgit(self, tmp_path):
        """Test that regular JSDoc blocks without @contextgit are ignored."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""/**
 * This is a regular JSDoc comment.
 * @param {string} name - The name parameter
 * @returns {boolean} - Returns true
 */
function greet(name) {
    return true;
}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_jsdoc_with_other_tags(self, tmp_path):
        """Test JSDoc block with @contextgit among other tags."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""/**
 * Process user data.
 *
 * @contextgit
 * id: C-019
 * type: code
 * title: User Data Processor
 *
 * @param {Object} user - The user object
 * @returns {Object} - Processed user
 */
function processUser(user) {
    return user;
}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "C-019"
        assert metadata.type == "code"
        assert metadata.title == "User Data Processor"

    def test_missing_required_field(self, tmp_path):
        """Test error when required field is missing."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""/**
 * @contextgit
 * id: C-001
 * type: code
 */
""")

        scanner = JavaScriptScanner()
        with pytest.raises(InvalidMetadataError, match="Missing 'title' field"):
            scanner.extract_metadata(file_path)

    def test_no_metadata(self, tmp_path):
        """Test file with no metadata returns empty list."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""// Regular JavaScript file
function main() {
    console.log('Hello');
}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_upstream_downstream_string_to_list(self, tmp_path):
        """Test that string upstream/downstream values are converted to lists."""
        file_path = tmp_path / "test.ts"
        file_path.write_text("""/**
 * @contextgit
 * id: C-001
 * type: code
 * title: Test
 * upstream: SR-001
 * downstream: T-001
 */
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].upstream == ["SR-001"]
        assert results[0].downstream == ["T-001"]

    def test_jsx_file(self, tmp_path):
        """Test parsing JSX file."""
        file_path = tmp_path / "component.jsx"
        file_path.write_text("""/**
 * @contextgit
 * id: C-020
 * type: code
 * title: React Component
 * tags: [react, ui]
 */

export default function MyComponent() {
    return <div>Hello</div>;
}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].id == "C-020"
        assert results[0].title == "React Component"

    def test_tsx_file(self, tmp_path):
        """Test parsing TSX file."""
        file_path = tmp_path / "component.tsx"
        file_path.write_text("""/**
 * @contextgit
 * id: C-021
 * type: code
 * title: TypeScript React Component
 */

interface Props {
    name: string;
}

export default function MyComponent({ name }: Props) {
    return <div>{name}</div>;
}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].id == "C-021"

    def test_es_module_extensions(self, tmp_path):
        """Test parsing .mjs and .cjs files."""
        # Test .mjs
        mjs_path = tmp_path / "module.mjs"
        mjs_path.write_text("""/**
 * @contextgit
 * id: C-022
 * type: code
 * title: ES Module
 */

export function test() {}
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(mjs_path)
        assert len(results) == 1
        assert results[0].id == "C-022"

        # Test .cjs
        cjs_path = tmp_path / "module.cjs"
        cjs_path.write_text("""/**
 * @contextgit
 * id: C-023
 * type: code
 * title: CommonJS Module
 */

module.exports = function test() {}
""")

        results = scanner.extract_metadata(cjs_path)
        assert len(results) == 1
        assert results[0].id == "C-023"

    def test_llm_generated_flag(self, tmp_path):
        """Test llm_generated flag is parsed correctly."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""/**
 * @contextgit
 * id: C-001
 * type: code
 * title: Test
 * llm_generated: true
 */
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].llm_generated is True

    def test_raw_content_captured(self, tmp_path):
        """Test that raw_content is captured for snippet extraction."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""/**
 * @contextgit
 * id: C-001
 * type: code
 * title: Test
 */
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].raw_content != ""
        assert "@contextgit" in results[0].raw_content

    def test_compact_jsdoc(self, tmp_path):
        """Test parsing compact JSDoc without extra asterisks."""
        file_path = tmp_path / "test.js"
        file_path.write_text("""/**
@contextgit
id: C-024
type: code
title: Compact Format
*/
""")

        scanner = JavaScriptScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].id == "C-024"
        assert results[0].title == "Compact Format"
