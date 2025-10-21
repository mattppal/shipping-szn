#!/usr/bin/env python3
"""Test media_files parameter validation in github_tools."""


def validate_media_files(media_files):
    """Test function that mimics the validation logic."""
    # Validate media_files is a list
    if media_files and not isinstance(media_files, list):
        return {
            "error": True,
            "message": f"Error: media_files must be a list, got {type(media_files).__name__}. Value: {repr(media_files)}",
        }
    return {"error": False, "value": media_files or []}


# Test cases
test_cases = [
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
]

print("Testing media_files validation:")
print("=" * 60)

all_passed = True
for i, (input_val, should_error, expected_value) in enumerate(test_cases, 1):
    result = validate_media_files(input_val)
    is_error = result["error"]
    passed = is_error == should_error

    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\nTest {i}: {status}")
    print(f"  Input:        {repr(input_val)}")
    print(f"  Should error: {should_error}")
    print(f"  Got error:    {is_error}")
    if is_error:
        print(f"  Error msg:    {result['message']}")
    else:
        print(f"  Value:        {result['value']}")

    if not passed:
        all_passed = False

print("\n" + "=" * 60)
if all_passed:
    print("✅ All tests passed!")
else:
    print("❌ Some tests failed!")

# Show the problematic case that was causing the error
print("\n" + "=" * 60)
print("The original error case:")
print("=" * 60)
problematic_input = "docs/updates/media/2025-10-21/lamp4-073802.mp4"
print(f"Input: {repr(problematic_input)}")
result = validate_media_files(problematic_input)
print(f"Result: {result}")
print("\nThis was being treated as a string and iterated character by character!")
print("Now it returns a clear error message instead of silently failing.")
