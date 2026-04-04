# tests/test_utils.py
"""Tests for utility functions in slipbox_mcp.utils."""
import logging
from datetime import datetime
from unittest.mock import patch

import pytest

from slipbox_mcp.models.schema import Link, LinkType
from slipbox_mcp.utils import format_note_for_display, parse_tags, setup_logging

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

SAMPLE_TAGS_CSV = "python, testing, notes"
EXPECTED_TAGS = ["python", "testing", "notes"]
SINGLE_TAG = "python"
TRAILING_COMMA_CSV = "python, testing,"

SAMPLE_TITLE = "Test Note"
SAMPLE_ID = "20250101T120000000000000"
SAMPLE_CONTENT = "This is the note body."
SAMPLE_CREATED = datetime(2025, 1, 1, 12, 0, 0)
SAMPLE_UPDATED = datetime(2025, 1, 2, 12, 0, 0)
SAMPLE_TAGS_LIST = ["python", "testing"]

LINK_TARGET_ID = "20250101T130000000000000"
LINK_DESCRIPTION = "See also this note"


# ---------------------------------------------------------------------------
# parse_tags
# ---------------------------------------------------------------------------


class TestParseTags:
    """Tests for the parse_tags utility."""

    def test_comma_separated_tags_are_split_and_stripped(self):
        # Arrange
        tags_str = SAMPLE_TAGS_CSV

        # Act
        result = parse_tags(tags_str)

        # Assert
        assert result == EXPECTED_TAGS, (
            f"Expected {EXPECTED_TAGS}, got {result}"
        )

    def test_empty_string_returns_empty_list(self):
        # Arrange
        tags_str = ""

        # Act
        result = parse_tags(tags_str)

        # Assert
        assert result == [], f"Expected empty list, got {result}"

    def test_trailing_comma_does_not_produce_empty_element(self):
        # Arrange
        tags_str = TRAILING_COMMA_CSV

        # Act
        result = parse_tags(tags_str)

        # Assert
        assert "" not in result, "Trailing comma produced an empty element"
        assert len(result) == 2, f"Expected 2 tags, got {len(result)}"

    def test_single_tag_without_comma(self):
        # Arrange
        tags_str = SINGLE_TAG

        # Act
        result = parse_tags(tags_str)

        # Assert
        assert result == [SINGLE_TAG], (
            f"Expected ['{SINGLE_TAG}'], got {result}"
        )


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    """Tests for the setup_logging utility."""

    @patch("slipbox_mcp.utils.logging.basicConfig")
    def test_valid_level_string_sets_numeric_level(self, mock_basic_config):
        # Arrange
        expected_level = logging.DEBUG

        # Act
        setup_logging(level="DEBUG")

        # Assert
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == expected_level, (
            f"Expected level={expected_level}, got {call_kwargs['level']}"
        )

    @patch("slipbox_mcp.utils.logging.basicConfig")
    def test_invalid_level_string_falls_back_to_info(self, mock_basic_config):
        # Arrange
        expected_level = logging.INFO

        # Act
        setup_logging(level="NONEXISTENT")

        # Assert
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == expected_level, (
            f"Expected fallback to INFO ({expected_level}), got {call_kwargs['level']}"
        )


# ---------------------------------------------------------------------------
# format_note_for_display
# ---------------------------------------------------------------------------


class TestFormatNoteForDisplay:
    """Tests for the format_note_for_display utility."""

    def test_basic_fields_appear_in_output(self):
        # Arrange / Act
        output = format_note_for_display(
            title=SAMPLE_TITLE,
            id=SAMPLE_ID,
            content=SAMPLE_CONTENT,
            tags=[],
            created_at=SAMPLE_CREATED,
            updated_at=SAMPLE_UPDATED,
        )

        # Assert
        assert f"# {SAMPLE_TITLE}" in output, "Title not found in output"
        assert f"ID: {SAMPLE_ID}" in output, "ID not found in output"
        assert SAMPLE_CONTENT in output, "Content not found in output"

    def test_tags_appear_when_provided(self):
        # Arrange / Act
        output = format_note_for_display(
            title=SAMPLE_TITLE,
            id=SAMPLE_ID,
            content=SAMPLE_CONTENT,
            tags=SAMPLE_TAGS_LIST,
            created_at=SAMPLE_CREATED,
            updated_at=SAMPLE_UPDATED,
        )

        # Assert
        assert "Tags:" in output, "Tags line missing from output"
        for tag in SAMPLE_TAGS_LIST:
            assert tag in output, f"Tag '{tag}' not found in output"

    def test_tags_absent_when_empty(self):
        # Arrange / Act
        output = format_note_for_display(
            title=SAMPLE_TITLE,
            id=SAMPLE_ID,
            content=SAMPLE_CONTENT,
            tags=[],
            created_at=SAMPLE_CREATED,
            updated_at=SAMPLE_UPDATED,
        )

        # Assert
        assert "Tags:" not in output, "Tags line should be absent for empty tags"

    def test_links_section_renders_with_description(self):
        # Arrange
        link = Link(
            source_id=SAMPLE_ID,
            target_id=LINK_TARGET_ID,
            link_type=LinkType.REFERENCE,
            description=LINK_DESCRIPTION,
        )

        # Act
        output = format_note_for_display(
            title=SAMPLE_TITLE,
            id=SAMPLE_ID,
            content=SAMPLE_CONTENT,
            tags=[],
            created_at=SAMPLE_CREATED,
            updated_at=SAMPLE_UPDATED,
            links=[link],
        )

        # Assert
        assert "## Links" in output, "Links header missing"
        assert LINK_TARGET_ID in output, "Link target_id missing"
        assert LINK_DESCRIPTION in output, "Link description missing"

    def test_links_section_renders_without_description(self):
        # Arrange
        link = Link(
            source_id=SAMPLE_ID,
            target_id=LINK_TARGET_ID,
            link_type=LinkType.REFERENCE,
        )

        # Act
        output = format_note_for_display(
            title=SAMPLE_TITLE,
            id=SAMPLE_ID,
            content=SAMPLE_CONTENT,
            tags=[],
            created_at=SAMPLE_CREATED,
            updated_at=SAMPLE_UPDATED,
            links=[link],
        )

        # Assert
        assert "## Links" in output, "Links header missing"
        assert LINK_TARGET_ID in output, "Link target_id missing"
        assert f"- {LinkType.REFERENCE.value}: {LINK_TARGET_ID}\n" in output, (
            "Link line without description not formatted correctly"
        )
