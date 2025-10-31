#!/usr/bin/env python3
"""Test that Slack file skip logic works correctly."""

import hashlib
from slugify import slugify

import pytest


# ============================================================================
# Helper Functions (mimics slack_tools logic)
# ============================================================================


def sanitize_filename(filename: str) -> str:
    """Test version of sanitize_filename."""
    if not filename:
        return "media"

    if "." in filename:
        name, ext = filename.rsplit(".", 1)
        ext = slugify(ext[:10])
    else:
        name = filename
        ext = ""

    name = slugify(name, max_length=40) or "media"
    return f"{name}.{ext}" if ext else name


def create_unique_filename(filename: str, file_id: str = "", url: str = "") -> str:
    """Test version of unique filename generation."""
    sanitized_name = sanitize_filename(filename)

    # Use file ID (stable) or URL (fallback)
    hash_source = file_id if file_id else url
    file_hash = hashlib.sha256(hash_source.encode()).hexdigest()[:12]

    if "." in sanitized_name:
        name_base, ext = sanitized_name.rsplit(".", 1)
        return f"{name_base}_{file_hash}.{ext}"
    else:
        return f"{sanitized_name}_{file_hash}"


# ============================================================================
# Scenario Tests
# ============================================================================


def test_same_file_different_url_tokens():
    """Test same file with different URL tokens should match."""
    file_id = "F12345ABCDE"
    filename = "My Cool Image.png"
    url1 = (
        "https://files.slack.com/files-pri/T123/F12345ABCDE/"
        "image.png?token=xoxe-abc123"
    )
    url2 = (
        "https://files.slack.com/files-pri/T123/F12345ABCDE/"
        "image.png?token=xoxe-xyz789"
    )

    result1 = create_unique_filename(filename, file_id=file_id, url=url1)
    result2 = create_unique_filename(filename, file_id=file_id, url=url2)

    assert (
        result1 == result2
    ), "Same file with different URL tokens should generate same filename"


def test_different_urls_without_file_id():
    """Test that URLs without file ID should NOT match."""
    filename = "My Cool Image.png"
    url1 = (
        "https://files.slack.com/files-pri/T123/F12345ABCDE/"
        "image.png?token=xoxe-abc123"
    )
    url2 = (
        "https://files.slack.com/files-pri/T123/F12345ABCDE/"
        "image.png?token=xoxe-xyz789"
    )

    result1 = create_unique_filename(filename, file_id="", url=url1)
    result2 = create_unique_filename(filename, file_id="", url=url2)

    assert (
        result1 != result2
    ), "Different URLs without file_id should generate different filenames"


def test_different_files_same_name():
    """Test that different files with same name should NOT match."""
    filename = "My Cool Image.png"
    file_id_a = "F12345ABCDE"
    file_id_b = "F67890FGHIJ"

    result_a = create_unique_filename(filename, file_id=file_id_a)
    result_b = create_unique_filename(filename, file_id=file_id_b)

    assert (
        result_a != result_b
    ), "Different files with same name should generate different filenames"


# ============================================================================
# Filename Sanitization Tests
# ============================================================================


@pytest.mark.parametrize(
    "filename",
    [
        "My Cool File (Final).mp4",
        "Screenshot 2025-01-15 @ 3:45 PM.png",
        "Design v2 — Updated [DRAFT].pdf",
        "北京_上海.jpg",  # Unicode
    ],
)
def test_filename_sanitization(filename):
    """Test filename sanitization with special characters."""
    sanitized = sanitize_filename(filename)
    result = create_unique_filename(filename, file_id="F123ABC")

    assert sanitized is not None
    assert len(sanitized) > 0
    assert result is not None
    assert len(result) > 0
    # Sanitized name should not contain special characters
    assert "(" not in sanitized or sanitized.index("(") < len(sanitized) - 10
    assert ")" not in sanitized or sanitized.index(")") < len(sanitized) - 10


def test_empty_filename():
    """Test that empty filename defaults to 'media'."""
    result = sanitize_filename("")
    assert result == "media"


def test_filename_without_extension():
    """Test filename without extension."""
    result = sanitize_filename("testfile")
    assert result is not None
    assert len(result) > 0


def test_unicode_filename():
    """Test unicode filename handling."""
    filename = "北京_上海.jpg"
    sanitized = sanitize_filename(filename)
    assert sanitized is not None
    assert "." in sanitized  # Extension should be preserved


# ============================================================================
# Hash Consistency Tests
# ============================================================================


def test_file_id_hash_consistency():
    """Test that same file_id always generates same hash."""
    filename = "test.png"
    file_id = "F12345ABCDE"

    result1 = create_unique_filename(filename, file_id=file_id)
    result2 = create_unique_filename(filename, file_id=file_id)

    assert result1 == result2, "Same file_id should generate same filename"


def test_url_hash_consistency():
    """Test that same URL always generates same hash."""
    filename = "test.png"
    url = "https://files.slack.com/files-pri/T123/F12345/image.png"

    result1 = create_unique_filename(filename, url=url)
    result2 = create_unique_filename(filename, url=url)

    assert result1 == result2, "Same URL should generate same filename"


# ============================================================================
# Hash Format Tests
# ============================================================================


def test_hash_length():
    """Test that hash is 12 characters."""
    filename = "test.png"
    file_id = "F12345ABCDE"

    result = create_unique_filename(filename, file_id=file_id)
    # Extract hash from result (between last _ and .)
    parts = result.rsplit("_", 1)
    if len(parts) > 1:
        hash_part = parts[1].split(".")[0]
        assert len(hash_part) == 12, "Hash should be 12 characters"


def test_hash_uniqueness():
    """Test that different file_ids generate different hashes."""
    filename = "test.png"
    file_ids = ["F111", "F222", "F333", "F444"]

    results = [create_unique_filename(filename, file_id=fid) for fid in file_ids]

    # All results should be unique
    assert len(results) == len(
        set(results)
    ), "Different file_ids should generate different filenames"


# ============================================================================
# Integration Test
# ============================================================================


def test_complete_filename_generation():
    """Test complete filename generation workflow."""
    filename = "My Cool File (Final).mp4"
    file_id = "F12345ABCDE"

    # Should not raise any errors
    result = create_unique_filename(filename, file_id=file_id)

    assert result is not None
    assert len(result) > 0
    assert file_id in result or "12345abcde" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
