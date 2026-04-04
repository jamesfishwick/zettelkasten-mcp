"""Test-specific fixtures (shared fixtures live in root conftest.py)."""
import pytest
from slipbox_mcp.services.search_service import SearchService


@pytest.fixture
def search_service(zettel_service):
    """Create a SearchService wired to the test ZettelService."""
    return SearchService(zettel_service)
