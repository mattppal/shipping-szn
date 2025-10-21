#!/usr/bin/env python3
"""Test that Slack file skip logic works correctly."""

import hashlib
from slugify import slugify


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


# Test cases
print("=" * 70)
print("Testing Slack File Skip Logic")
print("=" * 70)

# Simulate the same file downloaded twice with different URL tokens
file_id = "F12345ABCDE"
filename = "My Cool Image.png"
url1 = "https://files.slack.com/files-pri/T123/F12345ABCDE/image.png?token=xoxe-abc123"
url2 = "https://files.slack.com/files-pri/T123/F12345ABCDE/image.png?token=xoxe-xyz789"

print("\nScenario 1: Same file, different URL tokens (SHOULD MATCH)")
print("-" * 70)
result1 = create_unique_filename(filename, file_id=file_id, url=url1)
result2 = create_unique_filename(filename, file_id=file_id, url=url2)

print(f"Filename: {filename}")
print(f"File ID:  {file_id}")
print(f"URL 1:    {url1[:60]}...")
print(f"URL 2:    {url2[:60]}...")
print()
print(f"Result 1: {result1}")
print(f"Result 2: {result2}")
print(f"Match:    {'✅ YES' if result1 == result2 else '❌ NO'}")

# Test without file ID (old behavior - should NOT match)
print("\n\nScenario 2: Without file ID - URLs differ (SHOULD NOT MATCH)")
print("-" * 70)
result3 = create_unique_filename(filename, file_id="", url=url1)
result4 = create_unique_filename(filename, file_id="", url=url2)

print(f"Result 1: {result3}")
print(f"Result 2: {result4}")
print(f"Match:    {'✅ YES' if result3 == result4 else '❌ NO (expected)'}")

# Test different files with same name
print("\n\nScenario 3: Different files, same name (SHOULD NOT MATCH)")
print("-" * 70)
file_id_a = "F12345ABCDE"
file_id_b = "F67890FGHIJ"
result5 = create_unique_filename(filename, file_id=file_id_a)
result6 = create_unique_filename(filename, file_id=file_id_b)

print(f"File A ID: {file_id_a}")
print(f"File B ID: {file_id_b}")
print(f"Result A:  {result5}")
print(f"Result B:  {result6}")
print(f"Match:     {'✅ YES' if result5 == result6 else '❌ NO (expected)'}")

# Test filename sanitization
print("\n\nScenario 4: Special characters in filename")
print("-" * 70)
special_names = [
    "My Cool File (Final).mp4",
    "Screenshot 2025-01-15 @ 3:45 PM.png",
    "Design v2 — Updated [DRAFT].pdf",
    "北京_上海.jpg",  # Unicode
]

for name in special_names:
    sanitized = sanitize_filename(name)
    result = create_unique_filename(name, file_id="F123ABC")
    print(f"Original:   {name}")
    print(f"Sanitized:  {sanitized}")
    print(f"Final:      {result}")
    print()

print("=" * 70)
print("✅ Skip logic test complete!")
print()
print("Key insight: Using file_id ensures same file generates same hash,")
print("even when Slack URLs contain different authentication tokens.")
print("=" * 70)
