"""Simple, standalone Slack tools for Claude Agent SDK."""

import hashlib
import mimetypes
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv
from slugify import slugify

import requests
from claude_agent_sdk import tool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
if not SLACK_TOKEN:
    raise ValueError("SLACK_TOKEN is not set")

slack_client = WebClient(token=SLACK_TOKEN)

MAX_FILE_SIZE = 100 * 1024 * 1024
MEDIA_BASE_DIR = "./docs/updates/media"
MAX_CONCURRENT_DOWNLOADS = 5
MAX_TEXT_PREVIEW_LENGTH = 300
DEFAULT_DAYS_BACK = 7

# Module-level tracker for fetched message timestamps
# Structure: {channel_id: set of timestamps}
_fetched_timestamps: Dict[str, Set[str]] = defaultdict(set)


def track_fetched_timestamp(channel_id: str, timestamp: str) -> None:
    """Track a fetched message timestamp for later marking as processed."""
    _fetched_timestamps[channel_id].add(timestamp)


def get_fetched_timestamps() -> Dict[str, List[str]]:
    """Get all tracked timestamps grouped by channel."""
    return {channel: list(timestamps) for channel, timestamps in _fetched_timestamps.items()}


def clear_fetched_timestamps() -> None:
    """Clear all tracked timestamps (call after marking or on failure)."""
    _fetched_timestamps.clear()

import re

def strip_slack_emojis(text: str) -> str:
    """Remove Slack emoji shortcodes like :tada:, :ship:, :rocket: from text."""
    return re.sub(r':[a-zA-Z0-9_+-]+:', '', text).strip()

def clean_message_text(text: str, strip_emojis: bool = False) -> str:
    """Clean message text, optionally stripping emoji shortcodes."""
    if not text:
        return ""
    if strip_emojis:
        text = strip_slack_emojis(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage using slugify."""
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
        headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}

        sanitized_name = sanitize_filename(filename)

        hash_source = file_id if file_id else url
        file_hash = hashlib.sha256(hash_source.encode()).hexdigest()[:12]

        if "." in sanitized_name:
            name_base, ext = sanitized_name.rsplit(".", 1)
            unique_filename = f"{name_base}_{file_hash}.{ext}"
        else:
            unique_filename = f"{sanitized_name}_{file_hash}"

        date_str = datetime.now().strftime("%Y-%m-%d")
        media_dir = os.path.join(MEDIA_BASE_DIR, date_str)
        os.makedirs(media_dir, exist_ok=True)

        local_path = os.path.join(media_dir, unique_filename)

        if skip_existing and os.path.exists(local_path):
            existing_size = os.path.getsize(local_path)
            content_type, _ = mimetypes.guess_type(unique_filename)
            content_type = content_type or "application/octet-stream"

            return {
                "content": None,
                "filename": unique_filename,
                "mimetype": content_type,
                "local_path": local_path,
                "size": existing_size,
                "skipped": True,
            }

        response = requests.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()

        size_bytes = len(response.content)

        if size_bytes > MAX_FILE_SIZE:
            return None

        with open(local_path, "wb") as f:
            f.write(response.content)

        content_type = response.headers.get("content-type", "application/octet-stream")

        return {
            "content": response.content,
            "filename": unique_filename,
            "mimetype": content_type,
            "local_path": local_path,
            "size": size_bytes,
            "skipped": False,
        }

    except Exception as e:
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
        return []


def _download_single_file(file: Dict, skip_existing: bool) -> Optional[Dict]:
    """Helper function to download a single file."""
    file_id = file.get("id", "")
    filename = file.get("name", "unknown")

    if not file.get("url_private"):
        return None

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
    """Download and process files attached to a message in parallel."""
    if not files:
        return []

    processed_files = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(_download_single_file, file, skip_existing): file
            for file in files
        }

        for future in as_completed(future_to_file):
            try:
                result = future.result()
                if result:
                    processed_files.append(result)
            except Exception as e:
                file = future_to_file[future]
                logger.error(
                    f"Failed to download file {file.get('name', 'unknown')}: {str(e)}"
                )

    return processed_files


def has_processed_emoji(msg: Dict, emoji_name: str) -> bool:
    """Check if a message has the processed emoji reaction."""
    reactions = msg.get("reactions", [])
    return any(r.get("name") == emoji_name for r in reactions)


@tool(
    name="fetch_messages_from_channel",
    description="Fetch messages from a Slack channel within a specified time range. Downloads all media files (images, videos) to ./docs/updates/media/YYYY-MM-DD/. Options: ignore_processed_marker (default false) - if true, fetches ALL messages including those already marked with the processed emoji; strip_emojis (default false) removes :emoji: shortcodes from text.",
    input_schema={
        "channel_id": str,
        "days_back": int,
        "ignore_processed_marker": bool,
        "strip_emojis": bool,
    },
)
async def fetch_messages_from_channel(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch messages from a Slack channel with all media and threads.

    Args:
        channel_id: The Slack channel ID to fetch from
        days_back: Number of days back to fetch messages (default: 7)
        ignore_processed_marker: If true, include messages that already have the processed emoji (default: False, meaning skip already-processed messages)
        strip_emojis: If true, remove :emoji: shortcodes from message text (default: False)
    Returns a dictionary with content array for Claude Agent SDK.
    """
    strip_emojis = args.get("strip_emojis", False)
    ignore_processed_marker = args.get("ignore_processed_marker", False)
    skip_existing = True

    try:
        channel_id = args.get("channel_id")
        days_back = int(args.get("days_back", DEFAULT_DAYS_BACK))

        if not channel_id:
            return {
                "content": [{"type": "text", "text": "Error: channel_id is required"}],
                "is_error": True,
            }

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        messages = []

        result = slack_client.conversations_history(
            channel=channel_id,
            oldest=str(start_time.timestamp()),
            latest=str(end_time.timestamp()),
        )

        skipped_processed = 0
        for msg in result["messages"]:
            if not ignore_processed_marker and has_processed_emoji(msg, PROCESSED_EMOJI):
                skipped_processed += 1
                continue
                
            try:
                permalink_result = slack_client.chat_getPermalink(
                    channel=channel_id, message_ts=msg["ts"]
                )
                msg["permalink"] = permalink_result["permalink"]

                if msg.get("files"):
                    msg["processed_files"] = process_message_files(
                        msg["files"], skip_existing=skip_existing
                    )

                if msg.get("thread_ts"):
                    replies = get_thread_replies(channel_id, msg["thread_ts"])
                    for reply in replies:
                        if reply.get("files"):
                            reply["processed_files"] = process_message_files(
                                reply["files"], skip_existing=skip_existing
                            )
                    msg["replies"] = replies

                messages.append(msg)
                
                # Track this message timestamp for later marking as processed
                track_fetched_timestamp(channel_id, msg["ts"])

            except SlackApiError:
                continue

        summary = f"Fetched {len(messages)} messages from channel {channel_id}\n"
        summary += f"Time range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}\n"
        if skipped_processed > 0:
            summary += f"Skipped {skipped_processed} already-processed messages (had :{PROCESSED_EMOJI}: emoji)\n"
        if ignore_processed_marker:
            summary += f"Note: ignore_processed_marker=true - including ALL messages\n"
        summary += "\n"

        total_files = 0
        skipped_files = 0
        downloaded_files = 0
        for msg in messages:
            for file in msg.get("processed_files", []):
                total_files += 1
                if file.get("skipped"):
                    skipped_files += 1
                else:
                    downloaded_files += 1
            if msg.get("replies"):
                for reply in msg["replies"]:
                    for file in reply.get("processed_files", []):
                        total_files += 1
                        if file.get("skipped"):
                            skipped_files += 1
                        else:
                            downloaded_files += 1

        summary += f"Total media files: {total_files}\n"
        if skip_existing:
            summary += f"   Downloaded: {downloaded_files}\n"
            summary += f"   Skipped (already exist): {skipped_files}\n"
        else:
            summary += f"   Downloaded: {downloaded_files}\n"
        summary += f"   Location: {MEDIA_BASE_DIR}\n\n"
        summary += "=" * 60 + "\n\n"

        for i, msg in enumerate(messages, 1):
            summary += f"\nMessage {i}:\n"
            summary += f"   User: {msg.get('user', 'unknown')}\n"
            summary += f"   Timestamp: {datetime.fromtimestamp(float(msg.get('ts', 0))).strftime('%Y-%m-%d %H:%M:%S')}\n"

            text = msg.get("text", "")
            if len(text) > MAX_TEXT_PREVIEW_LENGTH:
                summary += f"   Text: {text[:MAX_TEXT_PREVIEW_LENGTH]}...\n"
            else:
                summary += f"   Text: {text}\n"

            summary += f"   Link: {msg.get('permalink', 'N/A')}\n"

            if msg.get("processed_files"):
                summary += f"   Files ({len(msg['processed_files'])}):\n"
                for file in msg["processed_files"]:
                    file_type = (
                        "Image"
                        if file.get("is_image")
                        else "Video" if file.get("is_video") else "File"
                    )
                    status = "Skipped: " if file.get("skipped") else ""
                    summary += f"      {status}{file_type}: {file['filename']}\n"
                    summary += f"        Path: {file['local_path']}\n"

            if msg.get("replies"):
                reply_count = len(msg["replies"])
                summary += f"   Thread: {reply_count} {'reply' if reply_count == 1 else 'replies'}\n"

                reply_files = 0
                for reply in msg["replies"]:
                    if reply.get("processed_files"):
                        reply_files += len(reply["processed_files"])

                if reply_files > 0:
                    summary += f"      Reply files: {reply_files}\n"

        return {
            "content": [
                {
                    "type": "text",
                    "text": summary,
                }
            ]
        }

    except SlackApiError as e:
        return {
            "content": [{"type": "text", "text": f"Slack API Error: {str(e)}"}],
            "is_error": True,
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Unexpected error: {str(e)}"}],
            "is_error": True,
        }


PROCESSED_EMOJI = "summarizer_ship"


@tool(
    name="mark_messages_processed",
    description=f"Add a :{PROCESSED_EMOJI}: reaction emoji to Slack messages to mark them as processed. Used for idempotency tracking to avoid re-processing the same messages.",
    input_schema={
        "channel_id": str,
        "message_timestamps": list,
    },
)
async def mark_messages_processed(args: dict[str, Any]) -> dict[str, Any]:
    """Add reaction emoji to processed Slack messages for idempotency.

    Args:
        args: Dictionary with:
            - channel_id: The Slack channel ID
            - message_timestamps: List of message 'ts' values to mark as processed

    Returns a dictionary with success/failure counts.
    """
    try:
        channel_id = args.get("channel_id")
        timestamps = args.get("message_timestamps", [])

        if not channel_id:
            return {
                "content": [{"type": "text", "text": "Error: channel_id is required"}],
                "is_error": True,
            }

        if not timestamps:
            return {
                "content": [{"type": "text", "text": "Error: message_timestamps is required and must not be empty"}],
                "is_error": True,
            }

        success_count = 0
        already_reacted = 0
        failed = []

        for ts in timestamps:
            try:
                slack_client.reactions_add(
                    channel=channel_id,
                    name=PROCESSED_EMOJI,
                    timestamp=ts
                )
                success_count += 1
            except SlackApiError as e:
                if e.response.get("error") == "already_reacted":
                    already_reacted += 1
                else:
                    failed.append({"ts": ts, "error": str(e)})

        summary = f"Marked {success_count} messages as processed with :{PROCESSED_EMOJI}:\n"
        if already_reacted > 0:
            summary += f"Skipped {already_reacted} messages (already marked)\n"
        if failed:
            summary += f"Failed to mark {len(failed)} messages:\n"
            for f in failed[:5]:
                summary += f"  - {f['ts']}: {f['error']}\n"
            if len(failed) > 5:
                summary += f"  ... and {len(failed) - 5} more\n"

        return {
            "content": [{"type": "text", "text": summary}],
        }

    except SlackApiError as e:
        return {
            "content": [{"type": "text", "text": f"Slack API Error: {str(e)}"}],
            "is_error": True,
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Unexpected error: {str(e)}"}],
            "is_error": True,
        }
