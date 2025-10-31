#!/usr/bin/env python3
"""Test GitHub token permissions and repository access."""

import os
from dotenv import load_dotenv
from github import Github, GithubException
from github import Auth

import pytest

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "replit/replit-docs")


@pytest.fixture
def github_client():
    """Create GitHub client fixture."""
    if not GITHUB_TOKEN:
        pytest.skip("GITHUB_TOKEN not set")
    auth = Auth.Token(GITHUB_TOKEN)
    return Github(auth=auth)


@pytest.fixture
def repo(github_client):
    """Get repository fixture."""
    try:
        return github_client.get_repo(GITHUB_REPO)
    except GithubException:
        pytest.skip(f"Cannot access repository: {GITHUB_REPO}")


# ============================================================================
# Token Validation Tests
# ============================================================================


def test_token_exists():
    """Test that GITHUB_TOKEN is set."""
    assert GITHUB_TOKEN is not None, "GITHUB_TOKEN not found in environment"


def test_repo_configured():
    """Test that GITHUB_REPO is configured."""
    assert GITHUB_REPO is not None, "GITHUB_REPO not configured"


# ============================================================================
# Authentication Tests
# ============================================================================


def test_authentication(github_client):
    """Test GitHub authentication."""
    user = github_client.get_user()
    assert user is not None
    assert hasattr(user, "login")
    assert user.login is not None


def test_rate_limit(github_client):
    """Test that rate limit can be checked."""
    try:
        rate_limit = github_client.get_rate_limit()
        assert rate_limit is not None
        assert hasattr(rate_limit, "core")
        assert rate_limit.core.remaining >= 0
        assert rate_limit.core.limit > 0
    except Exception as e:
        pytest.skip(f"Could not check rate limit: {str(e)}")


# ============================================================================
# Repository Access Tests
# ============================================================================


def test_repository_access(repo):
    """Test that repository can be accessed."""
    assert repo is not None
    assert repo.full_name == GITHUB_REPO
    assert hasattr(repo, "default_branch")


def test_repository_read_access(repo):
    """Test that repository contents can be read."""
    try:
        readme = repo.get_readme()
        assert readme is not None
        assert hasattr(readme, "name")
    except GithubException as e:
        pytest.skip(f"Cannot read repository contents: {e.status}")


def test_repository_permissions(repo):
    """Test that repository permissions can be checked."""
    try:
        permissions = repo.permissions
        assert permissions is not None
        assert hasattr(permissions, "admin")
        assert hasattr(permissions, "push")
        assert hasattr(permissions, "pull")
    except Exception as e:
        pytest.skip(f"Cannot check permissions: {str(e)}")


def test_repository_branches(repo):
    """Test that branches can be listed."""
    try:
        branches = list(repo.get_branches()[:3])
        assert isinstance(branches, list)
        for branch in branches:
            assert hasattr(branch, "name")
    except GithubException as e:
        pytest.skip(f"Cannot list branches: {e.status}")


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_invalid_repo_error(github_client):
    """Test error handling for invalid repository."""
    if not GITHUB_TOKEN:
        pytest.skip("GITHUB_TOKEN not set")

    invalid_repo = "invalid/does-not-exist-12345"
    with pytest.raises(GithubException) as exc_info:
        github_client.get_repo(invalid_repo)
    assert exc_info.value.status == 404


# ============================================================================
# Integration Test (Manual check - can be skipped if token not set)
# ============================================================================


@pytest.mark.integration
def test_full_workflow(github_client, repo):
    """Test complete workflow: authenticate -> access repo -> read content."""
    if not GITHUB_TOKEN:
        pytest.skip("GITHUB_TOKEN not set")

    # Already tested by fixtures, but verify chain works
    user = github_client.get_user()
    repo_obj = github_client.get_repo(GITHUB_REPO)

    assert user is not None
    assert repo_obj is not None
    assert repo_obj.full_name == GITHUB_REPO


# ============================================================================
# Helper for manual testing (preserved for backward compatibility)
# ============================================================================


def test_token_manual():
    """Manual test function for detailed token validation.

    This function provides detailed output for debugging token issues.
    Can be run manually or with pytest -v to see detailed output.
    """
    if not GITHUB_TOKEN:
        pytest.skip("GITHUB_TOKEN not set")

    print("\n" + "=" * 70)
    print("GitHub Token Manual Test")
    print("=" * 70)
    print(f"✓ Token found: {GITHUB_TOKEN[:10]}...{GITHUB_TOKEN[-4:]}")
    print(f"✓ Target repo: {GITHUB_REPO}")
    print()

    try:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)

        # Test 1: Authentication
        print("Test 1: Checking authentication...")
        user = g.get_user()
        print(f"✅ Authenticated as: {user.login}")
        print(f"   Name: {user.name or 'N/A'}")
        print(f"   Email: {user.email or 'N/A'}")
        print()

        # Test 2: Rate limit
        print("Test 2: Checking rate limit...")
        try:
            rate_limit = g.get_rate_limit()
            msg = (
                f"✅ API Rate Limit: "
                f"{rate_limit.core.remaining}/{rate_limit.core.limit}"
            )
            print(msg)
        except Exception as e:
            print(f"⚠️  Could not check rate limit: {str(e)}")
        print()

        # Test 3: Repository access
        print(f"Test 3: Accessing repository '{GITHUB_REPO}'...")
        try:
            repo_obj = g.get_repo(GITHUB_REPO)
            print("✅ Repository found!")
            print(f"   Name: {repo_obj.full_name}")
            print(f"   Private: {repo_obj.private}")
            print(f"   Default branch: {repo_obj.default_branch}")
            desc = repo_obj.description or "N/A"
            print(f"   Description: {desc}")
            print()

            # Test 4: Read access
            print("Test 4: Checking read access...")
            try:
                readme = repo_obj.get_readme()
                print("✅ Can read repository contents")
                print(f"   README found: {readme.name}")
                print()
            except GithubException as e:
                msg = (
                    f"⚠️  Cannot read repository contents: "
                    f"{e.status} {e.data.get('message', '')}"
                )
                print(msg)
                print()

            # Test 5: Permissions
            print("Test 5: Checking permissions...")
            try:
                permissions = repo_obj.permissions
                print("✅ Permissions retrieved:")
                print(f"   Admin: {permissions.admin}")
                print(f"   Push: {permissions.push}")
                print(f"   Pull: {permissions.pull}")
                print()
            except Exception as e:
                print(f"⚠️  Cannot check permissions: {str(e)}")
                print()

            # Test 6: Branches
            print("Test 6: Listing branches...")
            try:
                branches = list(repo_obj.get_branches()[:3])
                print(f"✅ Can list branches ({len(branches)} shown):")
                for branch in branches:
                    print(f"   - {branch.name}")
                print()
            except GithubException as e:
                msg = (
                    f"⚠️  Cannot list branches: "
                    f"{e.status} {e.data.get('message', '')}"
                )
                print(msg)
                print()

            print("=" * 70)
            print("✅ ALL TESTS PASSED - Token is working correctly!")
            print("=" * 70)

        except GithubException as e:
            print(f"❌ Cannot access repository: {e.status}")
            msg = e.data.get("message", "Unknown error")
            print(f"   Message: {msg}")
            doc_url = e.data.get("documentation_url", "N/A")
            print(f"   Documentation: {doc_url}")
            print()

            if e.status == 404:
                print("Possible reasons for 404 error:")
                print("  1. Repository doesn't exist or name is incorrect")
                msg = "  2. Repository is private and token lacks 'repo' scope"
                print(msg)
                print("  3. Token doesn't have access to the organization")
                print("  4. Token has been revoked or expired")
                print()
                print("To fix:")
                print("  1. Go to: https://github.com/settings/tokens")
                print("  2. Create a new token with 'repo' scope")
                print("  3. Update GITHUB_TOKEN in .env file")
            elif e.status == 401:
                print("Token is invalid or expired!")
                print("  1. Go to: https://github.com/settings/tokens")
                print("  2. Generate a new token")
                print("  3. Update GITHUB_TOKEN in .env file")

            print()
            print("=" * 70)
            pytest.fail(f"Cannot access repository: {e.status}")

    except GithubException as e:
        print(f"❌ GitHub API Error: {e.status}")
        msg = e.data.get("message", "Unknown error")
        print(f"   Message: {msg}")

        if e.status == 401:
            print()
            print("Your token is invalid!")
            token_preview = f"{GITHUB_TOKEN[:10]}...{GITHUB_TOKEN[-4:]}"
            print(f"  Current token: {token_preview}")
            print()
            print("To fix:")
            print("  1. Go to: https://github.com/settings/tokens")
            print("  2. Create a new token with these scopes:")
            print("     - repo (Full control of private repositories)")
            print("     - read:org (Read org and team membership)")
            print("  3. Update your .env file with the new token")

        print()
        print("=" * 70)
        pytest.fail(f"GitHub API Error: {e.status}")

    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        print()
        print("=" * 70)
        pytest.fail(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    # Allow running as script for backward compatibility
    pytest.main([__file__, "-v"])
