from __future__ import annotations

import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session

from . import drive_service, gmail_service
from .search_service import ingest_files


DEFAULT_GMAIL_QUERY = 'filename:("po" OR "purchase order") OR subject:("purchase order")'
DEFAULT_DRIVE_QUERY = 'fullText contains "purchase order" or fullText contains "PO"'

logger = logging.getLogger(__name__)


def perform_sync(
    db: Session,
    *,
    gmail_query: Optional[str] = None,
    drive_query: Optional[str] = None,
    gmail_limit: int = 30,
    drive_limit: int = 30,
    drive_folder_id: Optional[str] = None,
    enable_gmail: bool = True,
    enable_drive: bool = True,
) -> Dict[str, object]:
    """
    Perform synchronization of Purchase Order documents from Gmail and Google Drive.
    
    This function:
    1. Searches Gmail for PO-related email attachments
    2. Searches Google Drive for PO-related files (optionally from specific folder)
    3. Ingests found files into the database
    4. Tracks successes, duplicates, and errors
    
    Args:
        db: Database session
        gmail_query: Custom Gmail search query (optional)
        drive_query: Custom Drive search query (optional, ignored if drive_folder_id is set)
        gmail_limit: Maximum Gmail messages to fetch
        drive_limit: Maximum Drive files to fetch
        drive_folder_id: Specific Google Drive folder ID to sync from (optional)
        
    Returns:
        Dictionary containing sync summary with sources, counts, and errors
    """
    logger.info(
        "Starting sync operation (gmail_limit=%s, drive_limit=%s, folder_id=%s, enable_gmail=%s, enable_drive=%s)",
        gmail_limit,
        drive_limit,
        drive_folder_id or 'all',
        enable_gmail,
        enable_drive,
    )
    
    summary = {
        "sources": {
            "gmail": {
                "fetched": 0,
                "query": gmail_query or DEFAULT_GMAIL_QUERY,
                "error": None,
                "skipped": 0
            },
            "drive": {
                "fetched": 0,
                "query": drive_query or DEFAULT_DRIVE_QUERY,
                "error": None,
                "skipped": 0
            },
        },
        "ingested": 0,
        "duplicates": 0,
        "errors": [],
        "total_files_found": 0,
        "sync_duration_seconds": 0,
    }

    remote_files = []
    import time
    start_time = time.time()

    # Fetch from Gmail
    if enable_gmail:
        logger.info("Fetching attachments from Gmail...")
        try:
            gmail_results = gmail_service.search_gmail(
                gmail_query or DEFAULT_GMAIL_QUERY,
                max_results=gmail_limit
            )
            summary["sources"]["gmail"]["fetched"] = len(gmail_results)
            remote_files.extend(gmail_results)
            logger.info(f"Gmail fetch completed: {len(gmail_results)} attachments found")
        except RuntimeError as exc:
            error_msg = str(exc)
            summary["sources"]["gmail"]["error"] = error_msg
            logger.error(f"Gmail fetch failed: {error_msg}", exc_info=True)
        except Exception as exc:
            error_msg = f"Unexpected error during Gmail fetch: {exc}"
            summary["sources"]["gmail"]["error"] = error_msg
            logger.error(error_msg, exc_info=True)
    else:
        summary["sources"]["gmail"]["skipped"] = summary["sources"]["gmail"].get("skipped", 0) + 1
        summary["sources"]["gmail"]["reason"] = "disabled"
        logger.info("Gmail sync disabled; skipping Gmail fetch")

    # Fetch from Drive
    if enable_drive:
        if drive_folder_id:
            logger.info(f"Fetching files from specific Google Drive folder: {drive_folder_id}")
        else:
            logger.info("Fetching files from Google Drive (all accessible files)...")
        
        try:
            drive_results = drive_service.search_drive(
                drive_query or DEFAULT_DRIVE_QUERY,
                page_size=drive_limit,
                folder_id=drive_folder_id
            )
            summary["sources"]["drive"]["fetched"] = len(drive_results)
            summary["sources"]["drive"]["folder_id"] = drive_folder_id
            remote_files.extend(drive_results)
            logger.info(f"Drive fetch completed: {len(drive_results)} files found")
        except RuntimeError as exc:
            error_msg = str(exc)
            summary["sources"]["drive"]["error"] = error_msg
            logger.error(f"Drive fetch failed: {error_msg}", exc_info=True)
        except Exception as exc:
            error_msg = f"Unexpected error during Drive fetch: {exc}"
            summary["sources"]["drive"]["error"] = error_msg
            logger.error(error_msg, exc_info=True)
    else:
        summary["sources"]["drive"]["skipped"] = summary["sources"]["drive"].get("skipped", 0) + 1
        summary["sources"]["drive"]["reason"] = "disabled"
        logger.info("Drive sync disabled; skipping Drive fetch")

    summary["total_files_found"] = len(remote_files)
    
    if not remote_files:
        logger.warning("No files found from any source")
        summary["sync_duration_seconds"] = round(time.time() - start_time, 2)
        return summary

    # Ingest files into database
    logger.info(f"Ingesting {len(remote_files)} files into database...")
    try:
        ingest_summary = ingest_files(db, remote_files)
        summary["ingested"] = ingest_summary["ingested"]
        summary["duplicates"] = ingest_summary["duplicates"]
        summary["errors"].extend(ingest_summary["errors"])
        
        logger.info(f"Ingestion completed: {summary['ingested']} new, {summary['duplicates']} duplicates, {len(summary['errors'])} errors")
        
        # Log individual errors for debugging
        if summary["errors"]:
            logger.warning(f"Encountered {len(summary['errors'])} errors during ingestion:")
            for idx, error in enumerate(summary["errors"][:5], 1):  # Log first 5 errors
                logger.warning(f"  Error {idx}: {error}")
            if len(summary["errors"]) > 5:
                logger.warning(f"  ... and {len(summary['errors']) - 5} more errors")
        
        if summary["ingested"] > 0:
            logger.info("Committing changes to database...")
            db.commit()
            logger.info("Database commit successful")
        else:
            logger.info("No new files ingested, skipping commit")
            
    except Exception as exc:
        error_msg = f"Ingestion failed: {exc}"
        summary["errors"].append(error_msg)
        logger.error(error_msg, exc_info=True)
        db.rollback()
        logger.info("Database rolled back due to error")

    summary["sync_duration_seconds"] = round(time.time() - start_time, 2)
    
    # Final summary
    logger.info(
        f"Sync operation completed in {summary['sync_duration_seconds']}s: "
        f"Gmail={summary['sources']['gmail']['fetched']}, "
        f"Drive={summary['sources']['drive']['fetched']}, "
        f"Ingested={summary['ingested']}, "
        f"Duplicates={summary['duplicates']}, "
        f"Errors={len(summary['errors'])}"
    )
    
    return summary
