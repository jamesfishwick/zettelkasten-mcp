"""Tests for repository query methods."""
from slipbox_mcp.models.schema import LinkType


class TestFindOrphanedNotes:
    def test_no_links_returns_all(self, note_repository, zettel_service):
        n1 = zettel_service.create_note(title="Orphan 1", content="No links.")
        n2 = zettel_service.create_note(title="Orphan 2", content="No links.")
        orphans = note_repository.find_orphaned_notes()
        assert {n.id for n in orphans} == {n1.id, n2.id}

    def test_linked_notes_excluded(self, note_repository, zettel_service):
        n1 = zettel_service.create_note(title="Linked 1", content="Has link.")
        n2 = zettel_service.create_note(title="Linked 2", content="Has link.")
        zettel_service.create_link(n1.id, n2.id, LinkType.REFERENCE)
        orphans = note_repository.find_orphaned_notes()
        assert len(orphans) == 0


class TestFindCentralNotes:
    def test_returns_most_connected(self, note_repository, zettel_service):
        hub = zettel_service.create_note(title="Hub", content="Central.")
        n1 = zettel_service.create_note(title="Spoke 1", content="Connected.")
        n2 = zettel_service.create_note(title="Spoke 2", content="Connected.")
        zettel_service.create_link(hub.id, n1.id, LinkType.REFERENCE)
        zettel_service.create_link(hub.id, n2.id, LinkType.REFERENCE)
        results = note_repository.find_central_notes(limit=1)
        assert len(results) == 1
        assert results[0][0].id == hub.id
        assert results[0][1] >= 2
