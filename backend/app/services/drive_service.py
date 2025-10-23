from __future__ import annotations

import io
import logging
import time
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ..utils.auth import get_credentials

logger = logging.getLogger(__name__)


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


def _build_service():
    """Build Google Drive API service with credentials."""
    logger.debug("Building Google Drive API service")
    credentials = get_credentials()
    if not credentials:
        logger.error("Drive credentials not available")
        raise RuntimeError("Google credentials not configured. Visit /auth/login to connect.")
    logger.info("Google Drive API service built successfully")
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _build_query(query: str) -> str:
    """Build Drive API query string with MIME type filters."""
    sanitized = query.replace("'", "\\'")
    mime_filters = " or ".join([f"mimeType='{mime}'" for mime in SUPPORTED_MIME_TYPES])
    query_string = f"fullText contains '{sanitized}' and ({mime_filters})"
    logger.debug(f"Built Drive query: {query_string}")
    return query_string


def _get_files_recursive(service, folder_id: str, max_files: int = 100) -> List[Dict[str, Any]]:
    """
    Recursively get all files from a folder and its subfolders.
    
    Args:
        service: Google Drive service object
        folder_id: Folder ID to search recursively
        max_files: Maximum total files to retrieve
        
    Returns:
        List of file dictionaries
    """
    all_files = []
    folders_to_process = [folder_id]
    processed_folders = set()
    
    logger.info(f"Starting recursive search in folder {folder_id}")
    
    while folders_to_process and len(all_files) < max_files:
        current_folder = folders_to_process.pop(0)
        
        if current_folder in processed_folders:
            continue
        processed_folders.add(current_folder)
        
        try:
            # Get all items in current folder
            response = service.files().list(
                q=f"'{current_folder}' in parents and trashed=false",
                fields='files(id, name, mimeType, modifiedTime, owners/displayName, size)',
                pageSize=100
            ).execute()
            
            items = response.get('files', [])
            logger.debug(f"Folder {current_folder}: found {len(items)} items")
            
            for item in items:
                mime_type = item.get('mimeType')
                
                # If it's a folder, add to processing queue
                if mime_type == 'application/vnd.google-apps.folder':
                    folders_to_process.append(item['id'])
                    logger.debug(f"Found subfolder: {item['name']}")
                
                # If it's a supported file type, add to results
                elif mime_type in SUPPORTED_MIME_TYPES:
                    all_files.append(item)
                    logger.debug(f"Found file: {item['name']} ({mime_type})")
                    
                    if len(all_files) >= max_files:
                        logger.info(f"Reached max_files limit ({max_files}), stopping recursive search")
                        break
                        
        except Exception as exc:
            logger.error(f"Error processing folder {current_folder}: {exc}")
            continue
    
    logger.info(f"Recursive search completed: {len(all_files)} files found in {len(processed_folders)} folders")
    return all_files


def search_drive(query: str, page_size: int = 10, max_retries: int = 3, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search Google Drive for files matching query with retry logic.
    
    Args:
        query: Search query text
        page_size: Maximum number of files to retrieve
        max_retries: Maximum number of retry attempts for failed API calls
        folder_id: Optional specific folder ID to search within (searches recursively through subfolders)
        
    Returns:
        List of file dictionaries with metadata
    """
    logger.info(f"Starting Drive search with query: '{query}', page_size: {page_size}, folder_id: {folder_id or 'all'}")
    service = _build_service()
    
    # If folder_id specified, use recursive search
    if folder_id:
        logger.info(f"Using recursive search in folder: {folder_id}")
        files = _get_files_recursive(service, folder_id, max_files=page_size)
        
        # Format results to match expected structure
        results: List[Dict[str, Any]] = []
        for file in files:
            file_id = file.get('id')
            name = file.get('name')
            mime_type = file.get('mimeType')
            
            if not file_id or not name:
                continue
            
            file_size = file.get('size', 'unknown')
            logger.debug(f"Processing file: {name} ({mime_type}, {file_size} bytes)")
            
            file_info = {
                "file_id": file_id,
                "filename": name,
                "mime_type": mime_type,
                "source": "drive",
                "download_url": f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
                "metadata": {
                    "modified_time": file.get("modifiedTime"),
                    "owner": (file.get("owners") or [{}])[0].get("displayName"),
                    "size": file_size,
                },
            }
            results.append(file_info)
        
        logger.info(f"Recursive Drive search completed: {len(results)} files found")
        return results
    
    # Original query-based search (no folder specified)
    query_string = _build_query(query)

    # Search with retry logic
    for attempt in range(max_retries):
        try:
            logger.debug(f"Drive search attempt {attempt + 1}/{max_retries}")
            response = (
                service.files()
                .list(
                    q=query_string,
                    fields="files(id, name, mimeType, modifiedTime, owners/displayName, size)",
                    pageSize=page_size,
                    spaces="drive",
                )
                .execute()
            )
            logger.info(f"Drive search successful, found {len(response.get('files', []))} files")
            break
        except HttpError as exc:
            if attempt == max_retries - 1:
                logger.error(f"Drive search failed after {max_retries} attempts: {exc}", exc_info=True)
                raise RuntimeError(f"Drive search failed: {exc}") from exc
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(f"Drive search failed (attempt {attempt + 1}), retrying in {wait_time}s: {exc}")
            time.sleep(wait_time)

    files = response.get("files", []) or []
    results: List[Dict[str, Any]] = []
    skipped_files = 0
    
    logger.info(f"Processing {len(files)} Drive files")
    
    for idx, file in enumerate(files, 1):
        file_id = file.get("id")
        name = file.get("name")
        mime_type = file.get("mimeType")
        
        if not file_id or not name:
            logger.warning(f"File {idx} missing ID or name, skipping")
            skipped_files += 1
            continue
        
        file_size = file.get("size", "unknown")
        logger.debug(f"Processing file {idx}/{len(files)}: {name} ({mime_type}, {file_size} bytes)")
        
        file_info = {
            "file_id": file_id,
            "filename": name,
            "mime_type": mime_type,
            "source": "drive",
            "download_url": f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            "metadata": {
                "modified_time": file.get("modifiedTime"),
                "owner": (file.get("owners") or [{}])[0].get("displayName"),
                "size": file_size,
            },
        }
        results.append(file_info)
    
    logger.info(f"Drive search completed: {len(results)} files found, {skipped_files} files skipped")
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

