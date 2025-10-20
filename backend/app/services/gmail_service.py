from __future__ import annotations

import base64
import logging
import time
from typing import Any, Dict, Iterable, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..utils.auth import get_credentials

logger = logging.getLogger(__name__)


def _build_service():
    """Build Gmail API service with credentials."""
    logger.debug("Building Gmail API service")
    credentials = get_credentials()
    if not credentials:
        logger.error("Gmail credentials not available")
        raise RuntimeError("Google credentials not configured. Visit /auth/login to connect.")
    logger.info("Gmail API service built successfully")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def _extract_attachments(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    parts = payload.get("parts", []) or []
    for part in parts:
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            yield part
        # Recurse into nested parts
        if part.get("parts"):
            yield from _extract_attachments(part)


def search_gmail(query: str, max_results: int = 10, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    Search Gmail for messages and extract attachments with retry logic.
    
    Args:
        query: Gmail search query
        max_results: Maximum number of messages to retrieve
        max_retries: Maximum number of retry attempts for failed API calls
        
    Returns:
        List of attachment dictionaries with metadata
    """
    logger.info(f"Starting Gmail search with query: '{query}', max_results: {max_results}")
    service = _build_service()
    
    # Search for messages with retry logic
    for attempt in range(max_retries):
        try:
            logger.debug(f"Gmail search attempt {attempt + 1}/{max_retries}")
            response = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            logger.info(f"Gmail search successful, found {len(response.get('messages', []))} messages")
            break
        except HttpError as exc:
            if attempt == max_retries - 1:
                logger.error(f"Gmail search failed after {max_retries} attempts: {exc}", exc_info=True)
                raise RuntimeError(f"Gmail search failed: {exc}") from exc
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.warning(f"Gmail search failed (attempt {attempt + 1}), retrying in {wait_time}s: {exc}")
            time.sleep(wait_time)

    messages = response.get("messages", []) or []
    attachments: List[Dict[str, Any]] = []
    skipped_messages = 0
    
    logger.info(f"Processing {len(messages)} messages for attachments")

    for idx, message in enumerate(messages, 1):
        msg_id = message.get("id")
        if not msg_id:
            logger.warning(f"Message {idx} has no ID, skipping")
            skipped_messages += 1
            continue
            
        # Fetch message details with retry logic
        msg = None
        for attempt in range(max_retries):
            try:
                logger.debug(f"Fetching message {idx}/{len(messages)} (ID: {msg_id}), attempt {attempt + 1}")
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
                break
            except HttpError as exc:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch message {msg_id} after {max_retries} attempts: {exc}")
                    skipped_messages += 1
                    break
                wait_time = 2 ** attempt
                logger.warning(f"Failed to fetch message {msg_id} (attempt {attempt + 1}), retrying in {wait_time}s")
                time.sleep(wait_time)
        
        if not msg:
            continue

        payload = msg.get("payload", {})
        message_attachments = list(_extract_attachments(payload))
        logger.debug(f"Message {msg_id} has {len(message_attachments)} attachments")
        
        for part in message_attachments:
            attachment_id = part.get("body", {}).get("attachmentId")
            filename = part.get("filename")
            mime_type = part.get("mimeType")
            if not attachment_id or not filename:
                logger.warning(f"Attachment in message {msg_id} missing ID or filename, skipping")
                continue
            
            attachment_info = {
                "file_id": f"gmail::{msg_id}::{attachment_id}",
                "message_id": msg_id,
                "attachment_id": attachment_id,
                "filename": filename,
                "mime_type": mime_type,
                "source": "gmail",
                "download_url": f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/attachments/{attachment_id}",
            }
            attachments.append(attachment_info)
            logger.debug(f"Added attachment: {filename} ({mime_type}) from message {msg_id}")

    logger.info(f"Gmail search completed: {len(attachments)} attachments found, {skipped_messages} messages skipped")
    return attachments


def download_attachment(message_id: str, attachment_id: str) -> Optional[bytes]:
    service = _build_service()
    try:
        result = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
    except HttpError as exc:  # pragma: no cover - requires live API
        raise RuntimeError(f"Failed to download Gmail attachment: {exc}") from exc

    data = result.get("data")
    if not data:
        return None
    return base64.urlsafe_b64decode(data)

