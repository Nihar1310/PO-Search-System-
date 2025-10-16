from __future__ import annotations

from typing import Dict, Optional

from sqlalchemy.orm import Session

from . import drive_service, gmail_service
from .search_service import ingest_files


DEFAULT_GMAIL_QUERY = 'filename:("po" OR "purchase order") OR subject:("purchase order")'
DEFAULT_DRIVE_QUERY = 'fullText contains "purchase order" or fullText contains "PO"'


def perform_sync(
    db: Session,
    *,
    gmail_query: Optional[str] = None,
    drive_query: Optional[str] = None,
    gmail_limit: int = 30,
    drive_limit: int = 30,
) -> Dict[str, object]:
    summary = {
        "sources": {
            "gmail": {"fetched": 0, "query": gmail_query or DEFAULT_GMAIL_QUERY, "error": None},
            "drive": {"fetched": 0, "query": drive_query or DEFAULT_DRIVE_QUERY, "error": None},
        },
        "ingested": 0,
        "duplicates": 0,
        "errors": [],
    }

    remote_files = []

    try:
        gmail_results = gmail_service.search_gmail(gmail_query or DEFAULT_GMAIL_QUERY, max_results=gmail_limit)
        summary["sources"]["gmail"]["fetched"] = len(gmail_results)
        remote_files.extend(gmail_results)
    except RuntimeError as exc:
        summary["sources"]["gmail"]["error"] = str(exc)

    try:
        drive_results = drive_service.search_drive(drive_query or DEFAULT_DRIVE_QUERY, page_size=drive_limit)
        summary["sources"]["drive"]["fetched"] = len(drive_results)
        remote_files.extend(drive_results)
    except RuntimeError as exc:
        summary["sources"]["drive"]["error"] = str(exc)

    if not remote_files:
        return summary

    ingest_summary = ingest_files(db, remote_files)
    summary["ingested"] = ingest_summary["ingested"]
    summary["duplicates"] = ingest_summary["duplicates"]
    summary["errors"].extend(ingest_summary["errors"])

    if summary["ingested"]:
        db.commit()

    return summary
