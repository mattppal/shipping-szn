"""Simple, standalone Slack tools for Claude Agent SDK.

All Slack functionality in one file - no complex imports or nested modules.
"""

import logging
import mimetypes
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from claude_agent_sdk import tool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack client
slack_client = WebClient(token=os.getenv("SLACK_MCP_TOKEN"))

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MEDIA_BASE_DIR = "./docs/updates/media"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    words = text.split("-")
    slug = ""
    for word in words:
        if len(slug) + len(word) + 1 <= 50:
            slug = f"{slug}-{word}" if slug else word
        else:
            break
    return slug or "media"


def download_media_file(url: str, description: str = "") -> Optional[Dict]:
    """Download media file from Slack.

    Note: Slack's url_private already contains the token as a query parameter,
    so we don't need to add Authorization headers.
    """
    try:
        # Slack's url_private already includes authentication
        # Just add the Authorization header as backup
        headers = {"Authorization": f"Bearer {os.getenv('SLACK_MCP_TOKEN')}"}
        response = requests.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        # Get base filename from description and slugify it
        base_filename = slugify(description) if description else "media"

        # If slugify resulted in empty string, use default
        if not base_filename:
            base_filename = "media"

        # Get extension from content type
        extension = mimetypes.guess_extension(content_type) or ""
        if extension and extension.startswith("."):
            extension = extension[1:]  # Remove leading dot

        # Limit base filename length to ensure total path length is reasonable
        max_base_length = 50
        if len(base_filename) > max_base_length:
            base_filename = base_filename[:max_base_length].rstrip("-")

        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%H%M%S")
        filename = (
            f"{base_filename}-{timestamp}.{extension}"
            if extension
            else f"{base_filename}-{timestamp}"
        )

        size_bytes = len(response.content)

        if size_bytes > MAX_FILE_SIZE:
            logger.warning(f"File {filename} exceeds size limit")
            return None

        # Save to disk with date-based directory
        date_str = datetime.now().strftime("%Y-%m-%d")
        media_dir = os.path.join(MEDIA_BASE_DIR, date_str)
        os.makedirs(media_dir, exist_ok=True)

        local_path = os.path.join(media_dir, filename)
        with open(local_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Downloaded: {filename} ({size_bytes} bytes)")

        return {
            "content": response.content,
            "filename": filename,
            "mimetype": content_type,
            "local_path": local_path,
            "size": size_bytes,
        }

    except Exception as e:
        logger.error(f"Error downloading media: {str(e)}", exc_info=True)
        return None


def get_thread_replies(channel_id: str, thread_ts: str) -> List[Dict]:
    """Fetch all replies in a thread."""
    try:
        result = slack_client.conversations_replies(channel=channel_id, ts=thread_ts)
        replies = [msg for msg in result["messages"] if msg["ts"] != thread_ts]

        for reply in replies:
            try:
                permalink = slack_client.chat_getPermalink(
                    channel=channel_id, message_ts=reply["ts"]
                )
                reply["permalink"] = permalink["permalink"]
            except SlackApiError:
                reply["permalink"] = None

        return replies
    except SlackApiError as e:
        logger.error(f"Error fetching replies: {str(e)}")
        return []


def process_message_files(files: List[Dict], message_text: str) -> List[Dict]:
    """Download and process files attached to a message."""
    processed_files = []
    for file in files:
        if not file.get("url_private"):
            continue

        media_text = file.get("title") or file.get("name") or message_text
        media_data = download_media_file(file["url_private"], media_text)

        if media_data:
            processed = {
                "original_name": file.get("name"),
                "filename": media_data["filename"],
                "local_path": media_data["local_path"],
                "mimetype": media_data["mimetype"],
                "size": media_data["size"],
                "is_image": file.get("mimetype", "").startswith("image/"),
                "is_video": file.get("mimetype", "").startswith("video/"),
            }
            processed_files.append(processed)

    return processed_files


@tool(
    name="fetch_messages_from_channel",
    description="Fetch messages from a Slack channel within a specified time range. Downloads all media files (images, videos) to ./docs/updates/media/YYYY-MM-DD/. Processes main messages and thread replies.",
    input_schema={
        "channel_id": str,
        "days_back": int,
    },
)
async def fetch_messages_from_channel(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch messages from a Slack channel with all media and threads.

    Returns a dictionary with content array for Claude Agent SDK.
    """
    try:
        channel_id = args.get("channel_id")
        days_back = int(args.get("days_back", 7))

        if not channel_id:
            return {
                "content": [{"type": "text", "text": "Error: channel_id is required"}],
                "is_error": True,
            }

        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        logger.info(
            f"Fetching messages from channel {channel_id}: "
            f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}"
        )

        messages = []

        # Fetch messages from Slack
        result = slack_client.conversations_history(
            channel=channel_id,
            oldest=str(start_time.timestamp()),
            latest=str(end_time.timestamp()),
        )

        # Process each message
        for msg in result["messages"]:
            try:
                # Get permalink
                permalink_result = slack_client.chat_getPermalink(
                    channel=channel_id, message_ts=msg["ts"]
                )
                msg["permalink"] = permalink_result["permalink"]

                # Process files in main message
                if msg.get("files"):
                    msg["processed_files"] = process_message_files(
                        msg["files"], msg.get("text", "")
                    )

                # Process thread replies and their files
                if msg.get("thread_ts"):
                    replies = get_thread_replies(channel_id, msg["thread_ts"])
                    for reply in replies:
                        if reply.get("files"):
                            reply["processed_files"] = process_message_files(
                                reply["files"], reply.get("text", "")
                            )
                    msg["replies"] = replies

                messages.append(msg)

            except SlackApiError as e:
                logger.error(f"Error processing message: {str(e)}")
                continue

        # Format output for the agent
        summary = f"✅ Fetched {len(messages)} messages from channel {channel_id}\n"
        summary += f"📅 Time range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}\n\n"

        total_files = 0
        for msg in messages:
            files_count = len(msg.get("processed_files", []))
            if msg.get("replies"):
                for reply in msg["replies"]:
                    files_count += len(reply.get("processed_files", []))
            total_files += files_count

        summary += f"📎 Downloaded {total_files} media files to {MEDIA_BASE_DIR}\n\n"
        summary += "=" * 60 + "\n\n"

        # Add concise message details
        for i, msg in enumerate(messages, 1):
            summary += f"\n📝 Message {i}:\n"
            summary += f"   👤 User: {msg.get('user', 'unknown')}\n"
            summary += f"   📅 Timestamp: {datetime.fromtimestamp(float(msg.get('ts', 0))).strftime('%Y-%m-%d %H:%M:%S')}\n"

            text = msg.get("text", "")
            # Truncate very long messages
            if len(text) > 300:
                summary += f"   💬 Text: {text[:300]}...\n"
            else:
                summary += f"   💬 Text: {text}\n"

            summary += f"   🔗 Link: {msg.get('permalink', 'N/A')}\n"

            # List downloaded files with their types
            if msg.get("processed_files"):
                summary += f"   📎 Files ({len(msg['processed_files'])}):\n"
                for file in msg["processed_files"]:
                    file_type = "🖼️ Image" if file.get("is_image") else "🎥 Video" if file.get("is_video") else "📄 File"
                    summary += f"      {file_type}: {file['filename']}\n"
                    summary += f"        Path: {file['local_path']}\n"

            # Thread info
            if msg.get("replies"):
                reply_count = len(msg["replies"])
                summary += f"   💬 Thread: {reply_count} {'reply' if reply_count == 1 else 'replies'}\n"

                # List files from replies too
                reply_files = 0
                for reply in msg["replies"]:
                    if reply.get("processed_files"):
                        reply_files += len(reply["processed_files"])

                if reply_files > 0:
                    summary += f"      📎 Reply files: {reply_files}\n"

        return {
            "content": [
                {
                    "type": "text",
                    "text": summary,
                }
            ]
        }

    except SlackApiError as e:
        error_msg = f"Slack API Error: {str(e)}"
        logger.error(error_msg)
        return {
            "content": [{"type": "text", "text": error_msg}],
            "is_error": True,
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": [{"type": "text", "text": error_msg}],
            "is_error": True,
        }
