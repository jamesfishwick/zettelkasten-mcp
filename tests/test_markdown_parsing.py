"""Tests for markdown parsing helpers."""

from datetime import datetime

from slipbox_mcp.models.schema import LinkType
from slipbox_mcp.storage.note_repository import (
    _parse_frontmatter_dates,
    _parse_frontmatter_tags,
    _parse_links_section,
)


class TestParseFrontmatterTags:
    def test_from_comma_string(self):
        tags = _parse_frontmatter_tags("foo, bar, baz")
        assert [t.name for t in tags] == ["foo", "bar", "baz"]

    def test_from_list(self):
        tags = _parse_frontmatter_tags(["foo", "bar"])
        assert [t.name for t in tags] == ["foo", "bar"]

    def test_from_empty(self):
        assert _parse_frontmatter_tags("") == []
        assert _parse_frontmatter_tags(None) == []
        assert _parse_frontmatter_tags([]) == []

    def test_strips_whitespace(self):
        tags = _parse_frontmatter_tags("  foo , bar  ")
        assert [t.name for t in tags] == ["foo", "bar"]

    def test_filters_blank_entries(self):
        tags = _parse_frontmatter_tags("foo,,, bar,")
        assert [t.name for t in tags] == ["foo", "bar"]

    def test_list_with_non_strings(self):
        tags = _parse_frontmatter_tags([1, "bar"])
        assert [t.name for t in tags] == ["1", "bar"]

    def test_unexpected_type_returns_empty(self):
        tags = _parse_frontmatter_tags(42)
        assert tags == []


class TestParseLinksSection:
    def test_typed_links(self):
        content = (
            "Some content\n\n## Links\n"
            "- extends [[202101010000]] Some description\n"
            "- reference [[202101010001]]\n\n## Other"
        )
        links = _parse_links_section(content, source_id="test123")
        assert len(links) == 2
        assert links[0].link_type == LinkType.EXTENDS
        assert links[0].target_id == "202101010000"
        assert links[0].source_id == "test123"
        assert links[0].description == "Some description"
        assert links[1].link_type == LinkType.REFERENCE
        assert links[1].target_id == "202101010001"

    def test_no_links_section(self):
        links = _parse_links_section("No links section here", source_id="test123")
        assert links == []

    def test_unknown_link_type_defaults_to_reference(self):
        content = "## Links\n- unknown_type [[abc123]] desc\n"
        links = _parse_links_section(content, source_id="src")
        assert len(links) == 1
        assert links[0].link_type == LinkType.REFERENCE

    def test_empty_description_is_none_or_empty(self):
        content = "## Links\n- reference [[abc123]]\n"
        links = _parse_links_section(content, source_id="src")
        assert len(links) == 1
        # description should be None or empty string when not provided
        assert not links[0].description or links[0].description == ""

    def test_stops_at_next_heading(self):
        content = (
            "## Links\n- reference [[a]]\n"
            "## Next Section\n- reference [[b]]\n"
        )
        links = _parse_links_section(content, source_id="src")
        assert len(links) == 1
        assert links[0].target_id == "a"


class TestParseFrontmatterDates:
    def test_from_iso_strings(self):
        metadata = {
            "created": "2025-01-15T10:30:00",
            "updated": "2025-01-16T11:00:00",
        }
        created, updated = _parse_frontmatter_dates(metadata)
        assert created == datetime(2025, 1, 15, 10, 30, 0)
        assert updated == datetime(2025, 1, 16, 11, 0, 0)

    def test_missing_uses_defaults(self):
        created, updated = _parse_frontmatter_dates({})
        assert created is not None
        assert updated == created

    def test_missing_updated_defaults_to_created(self):
        metadata = {"created": "2025-06-01T12:00:00"}
        created, updated = _parse_frontmatter_dates(metadata)
        assert created == datetime(2025, 6, 1, 12, 0, 0)
        assert updated == created

    def test_missing_created_generates_now(self):
        before = datetime.now()
        created, updated = _parse_frontmatter_dates({})
        after = datetime.now()
        assert before <= created <= after
