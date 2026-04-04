# tests/test_utils.py
"""Tests for utility functions in slipbox_mcp.utils."""
import logging
from unittest.mock import patch


from slipbox_mcp.models.schema import Tag
from slipbox_mcp.utils import (
    content_preview,
    format_tags,
    parse_refs,
    parse_tags,
    setup_logging,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

SAMPLE_TAGS_CSV = "python, testing, notes"
EXPECTED_TAGS = ["python", "testing", "notes"]
SINGLE_TAG = "python"
TRAILING_COMMA_CSV = "python, testing,"


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
# parse_tags – None handling
# ---------------------------------------------------------------------------


class TestParseTagsNone:
    """Tests for parse_tags accepting None."""

    def test_none_returns_empty_list(self):
        assert parse_tags(None) == []

    def test_skips_empty_segments(self):
        assert parse_tags("poetry,,craft,") == ["poetry", "craft"]


# ---------------------------------------------------------------------------
# parse_refs
# ---------------------------------------------------------------------------


class TestParseRefs:
    """Tests for the parse_refs utility."""

    def test_empty_string(self):
        assert parse_refs("") == []

    def test_none(self):
        assert parse_refs(None) == []

    def test_single_ref(self):
        assert parse_refs("Ahrens (2017)") == ["Ahrens (2017)"]

    def test_multiple_refs(self):
        assert parse_refs("Ahrens (2017)\nhttps://example.com") == [
            "Ahrens (2017)",
            "https://example.com",
        ]

    def test_strips_whitespace(self):
        assert parse_refs("  Ahrens (2017) \n  https://example.com  ") == [
            "Ahrens (2017)",
            "https://example.com",
        ]

    def test_skips_empty_lines(self):
        assert parse_refs("Ahrens (2017)\n\nhttps://example.com\n") == [
            "Ahrens (2017)",
            "https://example.com",
        ]


# ---------------------------------------------------------------------------
# content_preview
# ---------------------------------------------------------------------------


class TestContentPreview:
    """Tests for the content_preview utility."""

    def test_short_content_unchanged(self):
        assert content_preview("hello world") == "hello world"

    def test_truncates_with_ellipsis(self):
        long = "a" * 200
        result = content_preview(long)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_replaces_newlines(self):
        assert content_preview("line1\nline2") == "line1 line2"

    def test_custom_max_length(self):
        result = content_preview("a" * 200, max_length=50)
        assert len(result) == 53


# ---------------------------------------------------------------------------
# format_tags
# ---------------------------------------------------------------------------


class TestFormatTags:
    """Tests for the format_tags utility."""

    def test_empty_list(self):
        assert format_tags([]) == ""

    def test_single_tag(self):
        assert format_tags([Tag(name="poetry")]) == "poetry"

    def test_multiple_tags(self):
        tags = [Tag(name="poetry"), Tag(name="craft")]
        assert format_tags(tags) == "poetry, craft"
