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
