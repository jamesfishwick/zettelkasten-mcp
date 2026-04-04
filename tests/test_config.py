"""Tests for configuration path expansion."""
import pytest
from slipbox_mcp.config import _expand_path


def test_expand_path_tilde_expands_to_absolute():
    result = _expand_path("~/notes")
    assert result.is_absolute(), f"Expected absolute path, got {result}"
    assert not str(result).startswith("~"), f"Tilde should be expanded, got {result}"


def test_expand_path_plain_relative_unchanged():
    result = _expand_path("data/notes")
    assert str(result) == "data/notes", f"Relative path should be unchanged, got {result}"


def test_expand_path_absolute_passthrough():
    result = _expand_path("/absolute/path")
    assert str(result) == "/absolute/path", f"Absolute path should pass through, got {result}"


def test_expand_path_nonexistent_user_raises():
    with pytest.raises(ValueError, match="could not be expanded"):
        _expand_path("~nonexistentuser_xyzzy/notes")


def test_expand_path_dot_unchanged():
    result = _expand_path(".")
    assert str(result) == ".", f"Dot should be unchanged, got {result}"
