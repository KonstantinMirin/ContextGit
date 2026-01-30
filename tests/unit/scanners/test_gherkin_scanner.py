"""Tests for Gherkin/Cucumber feature file scanner."""

import pytest
from pathlib import Path
from contextgit.scanners.gherkin import GherkinScanner
from contextgit.scanners.base import ExtractedMetadata
from contextgit.exceptions import InvalidMetadataError


class TestGherkinScanner:
    """Test cases for GherkinScanner."""

    def test_supported_extensions(self):
        """Test that scanner reports correct extensions."""
        scanner = GherkinScanner()
        assert scanner.supported_extensions == ['.feature']

    def test_parse_comment_block_at_file_start(self, tmp_path):
        """Test parsing comment block at file start (Feature level)."""
        file_path = tmp_path / "login.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: Login Feature Tests
# upstream: [SR-010]
# status: active

Feature: User Login
  As a user
  I want to login
  So that I can access my account

  Scenario: Successful login
    Given I am on the login page
    When I enter valid credentials
    Then I should be logged in
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "T-001"
        assert metadata.type == "test"
        assert metadata.title == "Login Feature Tests"
        assert metadata.upstream == ["SR-010"]
        assert metadata.status == "active"

    def test_parse_indented_comment_block(self, tmp_path):
        """Test parsing indented comment block (before Scenario)."""
        file_path = tmp_path / "login.feature"
        file_path.write_text("""Feature: User Login

  # @contextgit
  # id: T-002
  # type: test
  # title: Valid Login Scenario
  # upstream: [T-001]

  Scenario: Successful login with valid credentials
    Given I am on the login page
    When I enter valid username and password
    Then I should see the dashboard
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        metadata = results[0]
        assert metadata.id == "T-002"
        assert metadata.type == "test"
        assert metadata.title == "Valid Login Scenario"
        assert metadata.upstream == ["T-001"]

    def test_parse_multiple_blocks(self, tmp_path):
        """Test parsing multiple metadata blocks in one feature file."""
        file_path = tmp_path / "auth.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: Authentication Feature Tests
# upstream: [SR-010]

Feature: User Authentication
  Authentication scenarios for the application

  # @contextgit
  # id: T-002
  # type: test
  # title: Login Scenario
  # upstream: [T-001]

  Scenario: User logs in successfully
    Given I am on the login page
    When I enter valid credentials
    Then I am logged in

  # @contextgit
  # id: T-003
  # type: test
  # title: Logout Scenario
  # upstream: [T-001]

  Scenario: User logs out
    Given I am logged in
    When I click logout
    Then I am logged out
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 3
        assert results[0].id == "T-001"
        assert results[0].title == "Authentication Feature Tests"
        assert results[1].id == "T-002"
        assert results[1].title == "Login Scenario"
        assert results[2].id == "T-003"
        assert results[2].title == "Logout Scenario"

    def test_missing_required_field_id(self, tmp_path):
        """Test error when id field is missing."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# type: test
# title: Test Feature

Feature: Test
""")

        scanner = GherkinScanner()
        with pytest.raises(InvalidMetadataError, match="Missing 'id' field"):
            scanner.extract_metadata(file_path)

    def test_missing_required_field_type(self, tmp_path):
        """Test error when type field is missing."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# title: Test Feature

Feature: Test
""")

        scanner = GherkinScanner()
        with pytest.raises(InvalidMetadataError, match="Missing 'type' field"):
            scanner.extract_metadata(file_path)

    def test_missing_required_field_title(self, tmp_path):
        """Test error when title field is missing."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test

Feature: Test
""")

        scanner = GherkinScanner()
        with pytest.raises(InvalidMetadataError, match="Missing 'title' field"):
            scanner.extract_metadata(file_path)

    def test_no_metadata(self, tmp_path):
        """Test file with no contextgit metadata returns empty list."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# This is a regular comment
# about the feature

Feature: Simple Feature
  This feature has no contextgit metadata

  Scenario: Basic scenario
    Given something
    When action
    Then result
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_regular_comments_ignored(self, tmp_path):
        """Test that regular comments are ignored (not contextgit markers)."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# This is a regular comment
# Another regular comment
# id: FAKE-001
# type: should_be_ignored

Feature: Test Feature
  # This is a comment inside the feature
  # describing something

  Scenario: Test
    Given setup
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_upstream_downstream_string_to_list(self, tmp_path):
        """Test that string upstream/downstream values are converted to lists."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: Test Feature
# upstream: SR-001
# downstream: T-002

Feature: Test
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].upstream == ["SR-001"]
        assert results[0].downstream == ["T-002"]

    def test_llm_generated_flag(self, tmp_path):
        """Test llm_generated flag is parsed correctly."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: LLM Generated Test
# llm_generated: true

Feature: Generated Feature
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].llm_generated is True

    def test_raw_content_captured(self, tmp_path):
        """Test that raw_content is captured for snippet extraction."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: Test Feature

Feature: Test
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].raw_content != ""
        assert "@contextgit" in results[0].raw_content
        assert "id: T-001" in results[0].raw_content

    def test_line_number_tracking(self, tmp_path):
        """Test that line numbers are correctly tracked."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# Some header comment

# @contextgit
# id: T-001
# type: test
# title: Test Feature

Feature: Test
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        # @contextgit marker is on line 3 (1-indexed)
        assert results[0].line_number == 3

    def test_mixed_gherkin_tags_and_contextgit(self, tmp_path):
        """Test that Gherkin @tags don't interfere with @contextgit parsing."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: Tagged Feature
# tags: [smoke, regression]

@smoke @regression @wip
Feature: User Login
  Login feature with tags

  @critical
  Scenario: Important login test
    Given setup
    When action
    Then result
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].id == "T-001"
        assert results[0].tags == ["smoke", "regression"]

    def test_no_space_after_hash(self, tmp_path):
        """Test parsing comment blocks with no space after hash."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""#@contextgit
#id: T-001
#type: test
#title: No Space Test

Feature: Test
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].id == "T-001"

    def test_tags_as_list(self, tmp_path):
        """Test tags field as list is parsed correctly."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: Tagged Test
# tags: [integration, api, auth]

Feature: Test
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].tags == ["integration", "api", "auth"]

    def test_tags_as_string_converted_to_list(self, tmp_path):
        """Test tags field as string is converted to list."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: Single Tag Test
# tags: smoke

Feature: Test
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].tags == ["smoke"]

    def test_default_status_active(self, tmp_path):
        """Test that status defaults to 'active' when not specified."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: No Status Test

Feature: Test
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].status == "active"

    def test_multiple_upstream_values(self, tmp_path):
        """Test multiple upstream values in list format."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""# @contextgit
# id: T-001
# type: test
# title: Multi-Upstream Test
# upstream: [SR-001, SR-002, SR-003]

Feature: Test
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].upstream == ["SR-001", "SR-002", "SR-003"]

    def test_empty_file(self, tmp_path):
        """Test handling of empty feature file."""
        file_path = tmp_path / "empty.feature"
        file_path.write_text("")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 0

    def test_scenario_outline_with_metadata(self, tmp_path):
        """Test metadata block before Scenario Outline."""
        file_path = tmp_path / "test.feature"
        file_path.write_text("""Feature: Data-Driven Tests

  # @contextgit
  # id: T-001
  # type: test
  # title: Parameterized Login Test
  # upstream: [SR-005]

  Scenario Outline: Login with various credentials
    Given I am on the login page
    When I enter "<username>" and "<password>"
    Then I should see "<result>"

    Examples:
      | username | password | result  |
      | user1    | pass1    | success |
      | user2    | wrong    | failure |
""")

        scanner = GherkinScanner()
        results = scanner.extract_metadata(file_path)

        assert len(results) == 1
        assert results[0].id == "T-001"
        assert results[0].title == "Parameterized Login Test"
