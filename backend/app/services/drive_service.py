from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ..utils.auth import get_credentials


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


def _build_service():
    credentials = get_credentials()
    if not credentials:
        raise RuntimeError("Google credentials not configured. Visit /auth/login to connect.")
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _build_query(query: str) -> str:
    sanitized = query.replace("'", "\'")
    mime_filters = " or ".join([f"mimeType='{mime}'" for mime in SUPPORTED_MIME_TYPES])
    return f"fullText contains '{sanitized}' and ({mime_filters})"


def search_drive(query: str, page_size: int = 10) -> List[Dict[str, Any]]:
    service = _build_service()
    query_string = _build_query(query)

    try:
        response = (
            service.files()
            .list(
                q=query_string,
                fields="files(id, name, mimeType, modifiedTime, owners/displayName)",
                pageSize=page_size,
                spaces="drive",
            )
            .execute()
        )
    except HttpError as exc:  # pragma: no cover - requires live API
        raise RuntimeError(f"Drive search failed: {exc}") from exc

    files = response.get("files", []) or []
    results: List[Dict[str, Any]] = []
    for file in files:
        file_id = file.get("id")
        name = file.get("name")
        mime_type = file.get("mimeType")
        if not file_id or not name:
            continue
        results.append(
            {
                "file_id": file_id,
                "filename": name,
                "mime_type": mime_type,
                "source": "drive",
                "download_url": f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
                "metadata": {
                    "modified_time": file.get("modifiedTime"),
                    "owner": (file.get("owners") or [{}])[0].get("displayName"),
                },
            }
        )
    return results


def download_file(file_id: str) -> Optional[bytes]:
    service = _build_service()
    request = service.files().get_media(fileId=file_id)
    handle = io.BytesIO()

    try:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    except HttpError as exc:  # pragma: no cover - requires live API
        raise RuntimeError(f"Failed to download Drive file: {exc}") from exc

    return handle.getvalue()

