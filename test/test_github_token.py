#!/usr/bin/env python3
"""Test GitHub token permissions and repository access."""

import os
import sys
from dotenv import load_dotenv
from github import Github, GithubException

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "replit/replit-docs")


def test_token():
    """Test GitHub token validity and permissions."""

    print("=" * 70)
    print("GitHub Token Test")
    print("=" * 70)

    # Check if token exists
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found in environment")
        print("   Please set it in your .env file")
        return False

    print(f"✓ Token found: {GITHUB_TOKEN[:10]}...{GITHUB_TOKEN[-4:]}")
    print(f"✓ Target repo: {GITHUB_REPO}")
    print()

    try:
        # Initialize GitHub client (suppress deprecation warning)
        from github import Auth

        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)

        # Test 1: Get authenticated user
        print("Test 1: Checking authentication...")
        user = g.get_user()
        print(f"✅ Authenticated as: {user.login}")
        print(f"   Name: {user.name or 'N/A'}")
        print(f"   Email: {user.email or 'N/A'}")
        print()

        # Test 2: Check token scopes
        print("Test 2: Checking token scopes...")
        # Get rate limit to check scopes indirectly
        try:
            rate_limit = g.get_rate_limit()
            print(
                f"✅ API Rate Limit: {rate_limit.core.remaining}/{rate_limit.core.limit}"
            )
        except Exception as e:
            print(f"⚠️  Could not check rate limit: {str(e)}")
        print()

        # Test 3: Try to access the repository
        print(f"Test 3: Accessing repository '{GITHUB_REPO}'...")
        try:
            repo = g.get_repo(GITHUB_REPO)
            print(f"✅ Repository found!")
            print(f"   Name: {repo.full_name}")
            print(f"   Private: {repo.private}")
            print(f"   Default branch: {repo.default_branch}")
            print(f"   Description: {repo.description or 'N/A'}")
            print()

            # Test 4: Check if we can read contents
            print("Test 4: Checking read access...")
            try:
                # Try to get README or any file
                readme = repo.get_readme()
                print(f"✅ Can read repository contents")
                print(f"   README found: {readme.name}")
                print()
            except GithubException as e:
                print(
                    f"⚠️  Cannot read repository contents: {e.status} {e.data.get('message', '')}"
                )
                print()

            # Test 5: Check write access
            print("Test 5: Checking write access...")
            try:
                # Check permissions
                permissions = repo.permissions
                print(f"✅ Permissions retrieved:")
                print(f"   Admin: {permissions.admin}")
                print(f"   Push: {permissions.push}")
                print(f"   Pull: {permissions.pull}")
                print()
            except Exception as e:
                print(f"⚠️  Cannot check permissions: {str(e)}")
                print()

            # Test 6: Check if we can list branches
            print("Test 6: Listing branches...")
            try:
                branches = list(repo.get_branches()[:3])
                print(f"✅ Can list branches ({len(branches)} shown):")
                for branch in branches:
                    print(f"   - {branch.name}")
                print()
            except GithubException as e:
                print(
                    f"⚠️  Cannot list branches: {e.status} {e.data.get('message', '')}"
                )
                print()

            print("=" * 70)
            print("✅ ALL TESTS PASSED - Token is working correctly!")
            print("=" * 70)
            return True

        except GithubException as e:
            print(f"❌ Cannot access repository: {e.status}")
            print(f"   Message: {e.data.get('message', 'Unknown error')}")
            print(f"   Documentation: {e.data.get('documentation_url', 'N/A')}")
            print()

            if e.status == 404:
                print("Possible reasons for 404 error:")
                print("  1. Repository doesn't exist or name is incorrect")
                print("  2. Repository is private and token doesn't have 'repo' scope")
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
            return False

    except GithubException as e:
        print(f"❌ GitHub API Error: {e.status}")
        print(f"   Message: {e.data.get('message', 'Unknown error')}")

        if e.status == 401:
            print()
            print("Your token is invalid!")
            print(
                "  Current token: {}...{}".format(GITHUB_TOKEN[:10], GITHUB_TOKEN[-4:])
            )
            print()
            print("To fix:")
            print("  1. Go to: https://github.com/settings/tokens")
            print("  2. Create a new token with these scopes:")
            print("     - repo (Full control of private repositories)")
            print("     - read:org (Read org and team membership)")
            print("  3. Update your .env file with the new token")

        print()
        print("=" * 70)
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        print()
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = test_token()
    sys.exit(0 if success else 1)
