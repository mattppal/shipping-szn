#!/usr/bin/env python3
"""Tests for Slack tools functionality.

Run with: pytest test_slack_tools.py -v
"""

import os
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from slack_tools import (
    fetch_messages_from_channel,
    download_media_file,
    slugify,
    process_message_files,
    get_thread_replies,
)


class TestSlugify:
    """Test the slugify utility function."""

    def test_basic_slugify(self):
        """Test basic string slugification."""
        assert slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        """Test removal of special characters."""
        assert slugify("Hello@World#123!") == "helloworld123"

    def test_multiple_spaces(self):
        """Test handling of multiple spaces."""
        assert slugify("Hello   World") == "hello-world"

    def test_long_string_truncation(self):
        """Test that long strings are truncated to 50 chars."""
        long_string = "a" * 100
        result = slugify(long_string)
        assert len(result) <= 50

    def test_empty_string(self):
        """Test empty string returns default."""
        assert slugify("") == "media"

    def test_only_special_chars(self):
        """Test string with only special characters."""
        assert slugify("@#$%^&*()") == "media"


class TestDownloadMediaFile:
    """Test media file download functionality."""

    @patch("slack_tools.requests.get")
    @patch("slack_tools.os.makedirs")
    @patch("builtins.open", create=True)
    def test_successful_download(self, mock_open, mock_makedirs, mock_get):
        """Test successful file download."""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock file write
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = download_media_file("https://example.com/image.png", "test image")

        assert result is not None
        assert "filename" in result
        assert "local_path" in result
        assert "mimetype" in result
        assert result["mimetype"] == "image/png"
        assert result["size"] == len(b"fake image data")

    @patch("slack_tools.requests.get")
    def test_download_file_too_large(self, mock_get):
        """Test that files exceeding size limit are rejected."""
        # Mock response with large file
        mock_response = Mock()
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = b"x" * (101 * 1024 * 1024)  # 101MB
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = download_media_file("https://example.com/large.png", "large image")

        assert result is None

    @patch("slack_tools.requests.get")
    def test_download_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network error")

        result = download_media_file("https://example.com/image.png", "test")

        assert result is None


class TestProcessMessageFiles:
    """Test message file processing."""

    @patch("slack_tools.download_media_file")
    def test_process_single_file(self, mock_download):
        """Test processing a single file."""
        mock_download.return_value = {
            "filename": "test.png",
            "local_path": "/path/to/test.png",
            "mimetype": "image/png",
            "size": 1024,
            "content": b"fake",
        }

        files = [
            {
                "name": "test.png",
                "url_private": "https://example.com/test.png",
                "mimetype": "image/png",
            }
        ]

        result = process_message_files(files, "test message")

        assert len(result) == 1
        assert result[0]["filename"] == "test.png"
        assert result[0]["is_image"] is True

    def test_process_files_no_url(self):
        """Test that files without url_private are skipped."""
        files = [{"name": "test.png", "mimetype": "image/png"}]

        result = process_message_files(files, "test")

        assert len(result) == 0

    @patch("slack_tools.download_media_file")
    def test_process_video_file(self, mock_download):
        """Test processing a video file."""
        mock_download.return_value = {
            "filename": "video.mp4",
            "local_path": "/path/to/video.mp4",
            "mimetype": "video/mp4",
            "size": 2048,
            "content": b"fake",
        }

        files = [
            {
                "name": "video.mp4",
                "url_private": "https://example.com/video.mp4",
                "mimetype": "video/mp4",
            }
        ]

        result = process_message_files(files, "test")

        assert len(result) == 1
        assert result[0]["is_video"] is True
        assert result[0]["is_image"] is False


class TestGetThreadReplies:
    """Test thread reply fetching."""

    @patch("slack_tools.slack_client")
    def test_get_thread_replies_success(self, mock_client):
        """Test successful thread reply fetching."""
        mock_client.conversations_replies.return_value = {
            "messages": [
                {"ts": "1234.5678", "text": "Original"},
                {"ts": "1234.5679", "text": "Reply 1"},
                {"ts": "1234.5680", "text": "Reply 2"},
            ]
        }

        mock_client.chat_getPermalink.return_value = {
            "permalink": "https://example.slack.com/msg"
        }

        result = get_thread_replies("C123", "1234.5678")

        assert len(result) == 2  # Excludes original message
        assert result[0]["text"] == "Reply 1"
        assert result[1]["text"] == "Reply 2"

    @patch("slack_tools.slack_client")
    def test_get_thread_replies_error(self, mock_client):
        """Test handling of API errors."""
        from slack_sdk.errors import SlackApiError

        mock_client.conversations_replies.side_effect = SlackApiError(
            "Error", Mock(status_code=429)
        )

        result = get_thread_replies("C123", "1234.5678")

        assert result == []


class TestFetchMessagesFromChannel:
    """Test the main fetch_messages_from_channel function."""

    @pytest.mark.asyncio
    async def test_missing_channel_id(self):
        """Test error handling for missing channel_id."""
        result = await fetch_messages_from_channel({"days_back": 7})

        assert "content" in result
        assert "Error: channel_id is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    @patch("slack_tools.slack_client")
    async def test_fetch_empty_channel(self, mock_client):
        """Test fetching from a channel with no messages."""
        mock_client.conversations_history.return_value = {"messages": []}

        result = await fetch_messages_from_channel(
            {"channel_id": "C123", "days_back": 7}
        )

        assert "content" in result
        assert "Fetched 0 messages" in result["content"][0]["text"]

    @pytest.mark.asyncio
    @patch("slack_tools.slack_client")
    @patch("slack_tools.process_message_files")
    async def test_fetch_with_messages(self, mock_process_files, mock_client):
        """Test fetching messages with content."""
        mock_client.conversations_history.return_value = {
            "messages": [
                {
                    "ts": "1234.5678",
                    "user": "U123",
                    "text": "Test message",
                }
            ]
        }

        mock_client.chat_getPermalink.return_value = {
            "permalink": "https://example.slack.com/msg"
        }

        mock_process_files.return_value = []

        result = await fetch_messages_from_channel(
            {"channel_id": "C123", "days_back": 7}
        )

        assert "content" in result
        text = result["content"][0]["text"]
        assert "Fetched 1 messages" in text
        assert "Test message" in text

    @pytest.mark.asyncio
    @patch("slack_tools.slack_client")
    async def test_fetch_slack_api_error(self, mock_client):
        """Test handling of Slack API errors."""
        from slack_sdk.errors import SlackApiError

        mock_client.conversations_history.side_effect = SlackApiError(
            "Channel not found", Mock(status_code=404)
        )

        result = await fetch_messages_from_channel(
            {"channel_id": "C123", "days_back": 7}
        )

        assert "content" in result
        assert "Slack API Error" in result["content"][0]["text"]


@pytest.fixture
def mock_env_vars():
    """Fixture to set environment variables for tests."""
    original_token = os.environ.get("SLACK_MCP_XOXP_TOKEN")
    os.environ["SLACK_MCP_XOXP_TOKEN"] = "xoxp-test-token"

    yield

    if original_token:
        os.environ["SLACK_MCP_XOXP_TOKEN"] = original_token
    else:
        os.environ.pop("SLACK_MCP_XOXP_TOKEN", None)


class TestIntegration:
    """Integration tests (require real Slack token and channel)."""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("SLACK_MCP_XOXP_TOKEN") or not os.getenv("SLACK_CHANNEL_ID"),
        reason="Requires SLACK_MCP_XOXP_TOKEN and SLACK_CHANNEL_ID env vars",
    )
    @pytest.mark.asyncio
    async def test_real_channel_fetch(self):
        """Test fetching from a real Slack channel (integration test)."""
        channel_id = os.getenv("SLACK_CHANNEL_ID")

        result = await fetch_messages_from_channel(
            {"channel_id": channel_id, "days_back": 1}
        )

        assert "content" in result
        assert "Fetched" in result["content"][0]["text"]
