"""Tool chaining contracts -- verify tools compose correctly."""


class TestCreateThenSearch:
    def test_created_note_is_searchable(self, tool):
        """Create a note, then search for it by title -- should find it."""
        create_result = tool("zk_create_note")(
            title="Unique Searchable Concept",
            content="A note about a very unique concept for search testing.",
            tags="search-test",
        )
        note_id = create_result.split("ID: ")[1].strip()

        # Rebuild index to ensure FTS5 picks it up
        tool("zk_rebuild_index")()

        search_result = tool("zk_search_notes")(query="Unique Searchable Concept")
        assert note_id in search_result, "Created note should appear in search results"


class TestCreateLinkThenGet:
    def test_linked_note_appears_in_get_linked(self, tool):
        """Create two notes, link them, then verify get_linked_notes shows the link."""
        r1 = tool("zk_create_note")(title="Note Alpha", content="Alpha content")
        r2 = tool("zk_create_note")(title="Note Beta", content="Beta content")
        id1 = r1.split("ID: ")[1].strip()
        id2 = r2.split("ID: ")[1].strip()

        tool("zk_create_link")(
            source_id=id1,
            target_id=id2,
            link_type="extends",
            description="Alpha extends Beta",
        )

        linked = tool("zk_get_linked_notes")(note_id=id1, direction="outgoing")
        assert "Note Beta" in linked
        assert "extends" in linked.lower()
