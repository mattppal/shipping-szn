"""Simple, standalone Slack tools for Claude Agent SDK."""

import hashlib
import logging
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from slugify import slugify

import requests
from claude_agent_sdk import tool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
if not SLACK_TOKEN:
    raise ValueError("SLACK_TOKEN is not set")

# Initialize Slack client
slack_client = WebClient(token=SLACK_TOKEN)

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MEDIA_BASE_DIR = "./docs/updates/media"
MAX_CONCURRENT_DOWNLOADS = 5  # Maximum parallel downloads


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage using slugify.

    Uses python-slugify library for robust, standardized sanitization.
    """
    if not filename:
        return "media"

    # Split into name and extension
    if "." in filename:
        name, ext = filename.rsplit(".", 1)
        ext = slugify(ext[:10])  # Slugify and limit extension
    else:
        name = filename
        ext = ""

    # Slugify the name (handles unicode, special chars, spaces, etc.)
    # max_length=40 to keep filenames reasonable
    name = slugify(name, max_length=40) or "media"

    return f"{name}.{ext}" if ext else name


def download_media_file(
    url: str, filename: str = "", file_id: str = "", skip_existing: bool = True
) -> Optional[Dict]:
    """Download media file from Slack.

    Args:
        url: The URL to download from
        filename: The filename to use (should come from Slack's file.name field)
        file_id: Slack file ID for stable identification (URLs contain changing tokens)
        skip_existing: If True, skip download if file already exists (default: True)

    Note: Slack's url_private already contains the token as a query parameter,
    so we don't need to add Authorization headers.
    """
    try:
        # Slack's url_private already includes authentication
        # Just add the Authorization header as backup
        headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}

        # Sanitize the filename for safe filesystem usage
        sanitized_name = sanitize_filename(filename)

        # Create a unique hash from the file ID (stable) or URL (fallback)
        # File ID is stable, URL contains tokens that change
        hash_source = file_id if file_id else url
        file_hash = hashlib.sha256(hash_source.encode()).hexdigest()[:12]

        # Split name and extension
        if "." in sanitized_name:
            name_base, ext = sanitized_name.rsplit(".", 1)
            unique_filename = f"{name_base}_{file_hash}.{ext}"
        else:
            unique_filename = f"{sanitized_name}_{file_hash}"

        # Save to disk with date-based directory
        date_str = datetime.now().strftime("%Y-%m-%d")
        media_dir = os.path.join(MEDIA_BASE_DIR, date_str)
        os.makedirs(media_dir, exist_ok=True)

        local_path = os.path.join(media_dir, unique_filename)

        # Check if file already exists
        if skip_existing and os.path.exists(local_path):
            existing_size = os.path.getsize(local_path)
            logger.info(f"⏭️  Skipping download, file already exists: {unique_filename}")

            # Get content type from existing file
            content_type, _ = mimetypes.guess_type(unique_filename)
            content_type = content_type or "application/octet-stream"

            return {
                "content": None,  # Don't load content for existing files
                "filename": unique_filename,
                "mimetype": content_type,
                "local_path": local_path,
                "size": existing_size,
                "skipped": True,
            }

        # File doesn't exist or skip_existing is False, proceed with download
        response = requests.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()

        size_bytes = len(response.content)

        if size_bytes > MAX_FILE_SIZE:
            logger.warning(f"File {unique_filename} exceeds size limit")
            return None

        # Write file to disk
        with open(local_path, "wb") as f:
            f.write(response.content)

        content_type = response.headers.get("content-type", "application/octet-stream")
        logger.info(f"✅ Downloaded: {unique_filename} ({size_bytes} bytes)")

        return {
            "content": response.content,
            "filename": unique_filename,
            "mimetype": content_type,
            "local_path": local_path,
            "size": size_bytes,
            "skipped": False,
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


def _download_single_file(file: Dict, skip_existing: bool) -> Optional[Dict]:
    """Helper function to download a single file (used for parallel downloads)."""
    file_id = file.get("id", "")
    filename = file.get("name", "unknown")
    
    if not file.get("url_private"):
        logger.warning(
            f"⚠️  File '{filename}' (ID: {file_id}) has no url_private - skipping download. "
            "This may happen with files that require special permissions."
        )
        return None

    # Use the Slack filename directly (will be sanitized in download_media_file)
    media_data = download_media_file(
        file["url_private"], filename, file_id=file_id, skip_existing=skip_existing
    )

    if media_data:
        return {
            "original_name": file.get("name"),
            "filename": media_data["filename"],
            "local_path": media_data["local_path"],
            "mimetype": media_data["mimetype"],
            "size": media_data["size"],
            "is_image": file.get("mimetype", "").startswith("image/"),
            "is_video": file.get("mimetype", "").startswith("video/"),
            "skipped": media_data.get("skipped", False),
        }
    return None


def process_message_files(
    files: List[Dict],
    skip_existing: bool = True,
    max_workers: int = MAX_CONCURRENT_DOWNLOADS,
) -> List[Dict]:
    """Download and process files attached to a message in parallel.

    Args:
        files: List of file dictionaries from Slack API
        skip_existing: If True, skip downloading files that already exist
        max_workers: Maximum number of concurrent downloads (default: MAX_CONCURRENT_DOWNLOADS)
    """
    if not files:
        return []

    start_time = datetime.now()
    processed_files = []
    failed_files = []

    # Use ThreadPoolExecutor for parallel downloads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        future_to_file = {
            executor.submit(_download_single_file, file, skip_existing): file
            for file in files
        }

        # Collect results as they complete
        for future in as_completed(future_to_file):
            try:
                result = future.result()
                if result:
                    processed_files.append(result)
                else:
                    # Track files that failed to download (returned None)
                    file = future_to_file[future]
                    failed_files.append(file.get("name", "unknown"))
            except Exception as e:
                file = future_to_file[future]
                filename = file.get("name", "unknown")
                failed_files.append(filename)
                logger.error(
                    f"Error downloading file {filename}: {str(e)}", exc_info=True
                )

    elapsed = (datetime.now() - start_time).total_seconds()
    if processed_files:
        logger.info(
            f"Processed {len(processed_files)}/{len(files)} files in {elapsed:.2f}s "
            f"(parallel with {max_workers} workers)"
        )
    if failed_files:
        logger.warning(
            f"⚠️  Failed to download {len(failed_files)} file(s): "
            f"{', '.join(failed_files[:5])}"
            + (f" and {len(failed_files) - 5} more" if len(failed_files) > 5 else "")
        )

    return processed_files


@tool(
    name="fetch_messages_from_channel",
    description="Fetch messages from a Slack channel within a specified time range. Downloads all media files (images, videos) to ./docs/updates/media/YYYY-MM-DD/. Processes main messages and thread replies. Can skip downloading media files that already exist locally.",
    input_schema={
        "channel_id": str,
        "days_back": int,
    },
)
async def fetch_messages_from_channel(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch messages from a Slack channel with all media and threads.

    Args:
        channel_id: The Slack channel ID to fetch from
        days_back: Number of days back to fetch messages (default: 7)
    Returns a dictionary with content array for Claude Agent SDK.
    """
    skip_existing = True

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
                        msg["files"], skip_existing=skip_existing
                    )

                # Process thread replies and their files
                if msg.get("thread_ts"):
                    replies = get_thread_replies(channel_id, msg["thread_ts"])
                    for reply in replies:
                        if reply.get("files"):
                            reply["processed_files"] = process_message_files(
                                reply["files"], skip_existing=skip_existing
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
        skipped_files = 0
        downloaded_files = 0
        for msg in messages:
            files_count = len(msg.get("processed_files", []))
            for file in msg.get("processed_files", []):
                if file.get("skipped"):
                    skipped_files += 1
                else:
                    downloaded_files += 1
            if msg.get("replies"):
                for reply in msg["replies"]:
                    files_count += len(reply.get("processed_files", []))
                    for file in reply.get("processed_files", []):
                        if file.get("skipped"):
                            skipped_files += 1
                        else:
                            downloaded_files += 1
            total_files += files_count

        summary += f"📎 Total media files: {total_files}\n"
        if skip_existing:
            summary += f"   ✅ Downloaded: {downloaded_files}\n"
            summary += f"   ⏭️  Skipped (already exist): {skipped_files}\n"
        else:
            summary += f"   ✅ Downloaded: {downloaded_files}\n"
        summary += f"   📁 Location: {MEDIA_BASE_DIR}\n\n"
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
                    file_type = (
                        "🖼️ Image"
                        if file.get("is_image")
                        else "🎥 Video" if file.get("is_video") else "📄 File"
                    )
                    status = "⏭️ " if file.get("skipped") else ""
                    summary += f"      {status}{file_type}: {file['filename']}\n"
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
