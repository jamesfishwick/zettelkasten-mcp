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


class TestUpdateThenSearch:
    def test_update_then_search(self, tool):
        """Create note, update content, rebuild index, search for new content."""
        create_result = tool("zk_create_note")(
            title="Mutable Concept",
            content="Original content about widgets.",
        )
        note_id = create_result.split("ID: ")[1].strip()
        tool("zk_rebuild_index")()

        # Update content
        tool("zk_update_note")(note_id=note_id, content="Revised content about quantum entanglement.")
        tool("zk_rebuild_index")()

        search_result = tool("zk_search_notes")(query="quantum entanglement")
        assert note_id in search_result, "Updated note should appear in search for new content"


class TestDeleteThenGet:
    def test_delete_then_get(self, tool):
        """Create note, delete it, verify get returns 'not found'."""
        create_result = tool("zk_create_note")(
            title="Ephemeral Note", content="Soon to be gone."
        )
        note_id = create_result.split("ID: ")[1].strip()

        # Verify it exists
        get_result = tool("zk_get_note")(identifier=note_id)
        assert "# Ephemeral Note" in get_result

        # Delete
        tool("zk_delete_note")(note_id=note_id)

        # Verify gone
        get_after = tool("zk_get_note")(identifier=note_id)
        assert "not found" in get_after.lower()
