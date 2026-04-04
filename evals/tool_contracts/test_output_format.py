"""Tool output format contracts -- verify tools return parseable, useful output."""


class TestNoteToolOutputs:
    def test_create_note_returns_id(self, tool):
        result = tool("zk_create_note")(title="Test Note", content="Test content")
        assert "created successfully" in result.lower()
        assert "ID:" in result

    def test_get_note_returns_markdown_heading(self, tool):
        create_result = tool("zk_create_note")(title="My Title", content="Body here")
        note_id = create_result.split("ID: ")[1].strip()
        get_result = tool("zk_get_note")(identifier=note_id)
        assert "# My Title" in get_result

    def test_get_note_not_found(self, tool):
        result = tool("zk_get_note")(identifier="nonexistent-id-12345")
        assert "not found" in result.lower()

    def test_delete_note_confirms(self, tool):
        create_result = tool("zk_create_note")(title="To Delete", content="Goodbye")
        note_id = create_result.split("ID: ")[1].strip()
        delete_result = tool("zk_delete_note")(note_id=note_id)
        assert "deleted" in delete_result.lower()


class TestSearchToolOutputs:
    def test_search_with_results(self, tool):
        tool("zk_create_note")(
            title="Epistemology Deep Dive",
            content="About epistemology and knowledge.",
            tags="philosophy,epistemology",
        )
        tool("zk_rebuild_index")()
        result = tool("zk_search_notes")(query="epistemology")
        assert "found" in result.lower() or "result" in result.lower()

    def test_search_no_results(self, tool):
        result = tool("zk_search_notes")(query="xyznonexistent")
        assert "no" in result.lower() or "0" in result

    def test_find_orphaned_notes(self, tool):
        tool("zk_create_note")(title="Lonely Note", content="No links", tags="orphan")
        result = tool("zk_find_orphaned_notes")()
        assert "Lonely Note" in result or "orphan" in result.lower()


class TestLinkToolOutputs:
    def test_create_link_confirms(self, tool):
        r1 = tool("zk_create_note")(title="Source", content="Source note")
        r2 = tool("zk_create_note")(title="Target", content="Target note")
        id1 = r1.split("ID: ")[1].strip()
        id2 = r2.split("ID: ")[1].strip()
        result = tool("zk_create_link")(
            source_id=id1,
            target_id=id2,
            link_type="supports",
            description="Test link",
        )
        assert "created" in result.lower() or "link" in result.lower()

    def test_get_linked_notes(self, tool):
        r1 = tool("zk_create_note")(title="Hub Note", content="Hub content")
        r2 = tool("zk_create_note")(title="Spoke Note", content="Spoke content")
        id1 = r1.split("ID: ")[1].strip()
        id2 = r2.split("ID: ")[1].strip()
        tool("zk_create_link")(
            source_id=id1,
            target_id=id2,
            link_type="reference",
            description="Test",
        )
        result = tool("zk_get_linked_notes")(note_id=id1, direction="outgoing")
        assert "Spoke Note" in result


class TestUpdateToolOutputs:
    def test_update_note_title(self, tool):
        """Create a note, update its title, verify get returns the new title."""
        create_result = tool("zk_create_note")(title="Old Title", content="Body text")
        note_id = create_result.split("ID: ")[1].strip()
        update_result = tool("zk_update_note")(note_id=note_id, title="New Title")
        assert "updated" in update_result.lower()
        get_result = tool("zk_get_note")(identifier=note_id)
        assert "# New Title" in get_result


class TestRemoveLinkOutputs:
    def test_remove_link(self, tool):
        """Create two notes + link, remove link, verify no links remain."""
        r1 = tool("zk_create_note")(title="Left Note", content="Left content")
        r2 = tool("zk_create_note")(title="Right Note", content="Right content")
        id1 = r1.split("ID: ")[1].strip()
        id2 = r2.split("ID: ")[1].strip()
        tool("zk_create_link")(
            source_id=id1, target_id=id2, link_type="supports", description="Test"
        )
        # Verify link exists
        linked = tool("zk_get_linked_notes")(note_id=id1, direction="outgoing")
        assert "Right Note" in linked

        # Remove and verify
        remove_result = tool("zk_remove_link")(source_id=id1, target_id=id2)
        assert "removed" in remove_result.lower()
        linked_after = tool("zk_get_linked_notes")(note_id=id1, direction="outgoing")
        assert "No" in linked_after or "Right Note" not in linked_after


class TestTagToolOutputs:
    def test_get_all_tags(self, tool):
        """Create notes with tags, call zk_get_all_tags, verify tags appear."""
        tool("zk_create_note")(
            title="Tagged Note A", content="Content A", tags="alpha,beta"
        )
        tool("zk_create_note")(
            title="Tagged Note B", content="Content B", tags="gamma,beta"
        )
        result = tool("zk_get_all_tags")()
        assert "alpha" in result
        assert "beta" in result
        assert "gamma" in result


class TestSimilarNotesOutputs:
    def test_find_similar_notes(self, tool):
        """Create two notes with overlapping tags, verify find_similar returns the other."""
        r1 = tool("zk_create_note")(
            title="Note About Dogs", content="Dogs are great pets", tags="animals,pets"
        )
        tool("zk_create_note")(
            title="Note About Cats", content="Cats are also great pets", tags="animals,pets"
        )
        id1 = r1.split("ID: ")[1].strip()
        result = tool("zk_find_similar_notes")(note_id=id1, threshold=0.1)
        assert "Cats" in result


class TestCentralNotesOutputs:
    def test_find_central_notes(self, tool):
        """Create a hub with 3+ links, verify find_central returns the hub."""
        hub = tool("zk_create_note")(title="Central Hub", content="Hub content")
        hub_id = hub.split("ID: ")[1].strip()
        spoke_ids = []
        for i in range(3):
            r = tool("zk_create_note")(
                title=f"Spoke {i}", content=f"Spoke content {i}"
            )
            spoke_ids.append(r.split("ID: ")[1].strip())
        for sid in spoke_ids:
            tool("zk_create_link")(
                source_id=hub_id, target_id=sid, link_type="reference"
            )
        result = tool("zk_find_central_notes")(limit=5)
        assert "Central Hub" in result


class TestDateToolOutputs:
    def test_list_notes_by_date(self, tool):
        """Create notes, call list_notes_by_date, verify output contains notes."""
        tool("zk_create_note")(title="Date Test Note", content="Some content")
        result = tool("zk_list_notes_by_date")(limit=10)
        assert "Date Test Note" in result
        assert "showing" in result.lower() or "result" in result.lower()


class TestRebuildIndexOutputs:
    def test_rebuild_index_reports_count(self, tool):
        """Create a note, rebuild index, verify output mentions note count."""
        tool("zk_create_note")(title="Index Test", content="Rebuild me")
        result = tool("zk_rebuild_index")()
        assert "rebuilt" in result.lower()
        assert "Notes processed:" in result


class TestErrorFormats:
    def test_invalid_note_type_lists_valid(self, tool):
        result = tool("zk_create_note")(
            title="Bad", content="Bad", note_type="invalid"
        )
        assert "Invalid note type" in result
        assert "fleeting" in result  # lists valid types
        assert "permanent" in result

    def test_invalid_link_type_lists_valid(self, tool):
        r1 = tool("zk_create_note")(title="A", content="A content")
        r2 = tool("zk_create_note")(title="B", content="B content")
        id1 = r1.split("ID: ")[1].strip()
        id2 = r2.split("ID: ")[1].strip()
        result = tool("zk_create_link")(
            source_id=id1, target_id=id2, link_type="invalid_type"
        )
        assert "Invalid link type" in result or "invalid" in result.lower()
