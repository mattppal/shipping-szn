#!/usr/bin/env python3
"""Test media_files parameter validation in github_tools."""

import pytest


# ============================================================================
# Validation Logic (mimics github_tools logic)
# ============================================================================


def validate_media_files(media_files):
    """Test function that mimics the validation logic."""
    # Validate media_files is a list
    if media_files and not isinstance(media_files, list):
        return {
            "error": True,
            "message": (
                f"Error: media_files must be a list, got "
                f"{type(media_files).__name__}. Value: {repr(media_files)}"
            ),
        }
    return {"error": False, "value": media_files or []}


# ============================================================================
# Test Cases
# ============================================================================


@pytest.mark.parametrize(
    "input_val,should_error,expected_value",
    [
        # Valid list input - should pass
        (["file1.png", "file2.mp4"], False, ["file1.png", "file2.mp4"]),
        # String input - should fail
        ("file1.png", True, None),
        # Empty list - should pass
        ([], False, []),
        # None - should pass (treated as empty)
        (None, False, []),
        # Empty string - treated as empty (falsy value)
        ("", False, []),
        # Invalid type (number) - should fail
        (123, True, None),
        # Invalid type (dict) - should fail
        ({"file": "test.png"}, True, None),
    ],
)
def test_media_files_validation(input_val, should_error, expected_value):
    """Test media_files validation with various input types."""
    result = validate_media_files(input_val)
    is_error = result["error"]

    assert (
        is_error == should_error
    ), f"Validation error mismatch: expected {should_error}, got {is_error}"

    if not is_error:
        assert (
            result["value"] == expected_value
        ), f"Value mismatch: expected {expected_value}, got {result['value']}"


# ============================================================================
# Specific Test Cases
# ============================================================================


def test_media_files_valid_list():
    """Test that valid list passes validation."""
    result = validate_media_files(["file1.png", "file2.mp4"])
    assert result["error"] is False
    assert result["value"] == ["file1.png", "file2.mp4"]


def test_media_files_string_fails():
    """Test that string input fails validation."""
    problematic_input = "docs/updates/media/2025-10-21/lamp4-073802.mp4"
    result = validate_media_files(problematic_input)
    assert result["error"] is True
    assert "must be a list" in result["message"]
    assert "str" in result["message"] or "string" in result["message"].lower()


def test_media_files_empty_list():
    """Test that empty list passes validation."""
    result = validate_media_files([])
    assert result["error"] is False
    assert result["value"] == []


def test_media_files_none():
    """Test that None passes validation (treated as empty)."""
    result = validate_media_files(None)
    assert result["error"] is False
    assert result["value"] == []


def test_media_files_empty_string():
    """Test that empty string passes validation (falsy)."""
    result = validate_media_files("")
    assert result["error"] is False
    assert result["value"] == []


def test_media_files_number_fails():
    """Test that number input fails validation."""
    result = validate_media_files(123)
    assert result["error"] is True
    assert "must be a list" in result["message"]


def test_media_files_dict_fails():
    """Test that dict input fails validation."""
    result = validate_media_files({"file": "test.png"})
    assert result["error"] is True
    assert "must be a list" in result["message"]


# ============================================================================
# Edge Cases
# ============================================================================


def test_media_files_unicode_paths():
    """Test that list with unicode paths passes validation."""
    result = validate_media_files(["北京_上海.jpg", "test.png"])
    assert result["error"] is False
    assert len(result["value"]) == 2


def test_media_files_long_list():
    """Test that long list passes validation."""
    large_list = [f"file{i}.png" for i in range(100)]
    result = validate_media_files(large_list)
    assert result["error"] is False
    assert len(result["value"]) == 100


# ============================================================================
# Documentation Test (shows original error case)
# ============================================================================


def test_problematic_string_case():
    """Test the original problematic case that caused errors.

    This was being treated as a string and iterated character by character!
    Now it returns a clear error message instead of silently failing.
    """
    problematic_input = "docs/updates/media/2025-10-21/lamp4-073802.mp4"
    result = validate_media_files(problematic_input)

    assert result["error"] is True
    assert "must be a list" in result["message"]
    assert problematic_input in result["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
