from __future__ import annotations

import base64
from typing import Any, Dict, Iterable, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..utils.auth import get_credentials


def _build_service():
    credentials = get_credentials()
    if not credentials:
        raise RuntimeError("Google credentials not configured. Visit /auth/login to connect.")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def _extract_attachments(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    parts = payload.get("parts", []) or []
    for part in parts:
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            yield part
        # Recurse into nested parts
        if part.get("parts"):
            yield from _extract_attachments(part)


def search_gmail(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    service = _build_service()

    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
    except HttpError as exc:  # pragma: no cover - requires live API
        raise RuntimeError(f"Gmail search failed: {exc}") from exc

    messages = response.get("messages", []) or []
    attachments: List[Dict[str, Any]] = []

    for message in messages:
        msg_id = message.get("id")
        if not msg_id:
            continue
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
        except HttpError as exc:  # pragma: no cover - requires live API
            # Skip messages we cannot fetch
            continue

        payload = msg.get("payload", {})
        for part in _extract_attachments(payload):
            attachment_id = part.get("body", {}).get("attachmentId")
            filename = part.get("filename")
            mime_type = part.get("mimeType")
            if not attachment_id or not filename:
                continue
            attachments.append(
                {
                    "file_id": f"gmail::{msg_id}::{attachment_id}",
                    "message_id": msg_id,
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "source": "gmail",
                    "download_url": f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/attachments/{attachment_id}",
                }
            )

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

