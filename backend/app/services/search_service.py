from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from dateutil import parser as date_parser
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models import PO
from . import drive_service, gmail_service, parser_service


def search_pos(db: Session, query: str, limit: int = 50) -> List[PO]:
    if not query:
        return []

    cached = _search_cache(db, query, limit)
    if cached:
        return cached

    remote_files, _ = collect_remote_files(query)
    if not remote_files:
        return cached

    summary = ingest_files(db, remote_files)
    if summary["ingested"]:
        db.commit()

    return _search_cache(db, query, limit)


def collect_remote_files(query: str, limit: int = 25) -> Tuple[List[Dict], List[str]]:
    remote_files: List[Dict] = []
    errors: List[str] = []

    try:
        remote_files.extend(gmail_service.search_gmail(query, max_results=limit))
    except RuntimeError as exc:
        errors.append(f"gmail:{exc}")

    try:
        remote_files.extend(drive_service.search_drive(query, page_size=limit))
    except RuntimeError as exc:
        errors.append(f"drive:{exc}")

    return remote_files, errors


def _search_cache(db: Session, query: str, limit: int) -> List[PO]:
    q = f"%{query.lower()}%"
    return (
        db.query(PO)
        .filter(
            or_(
                func.lower(PO.po_number).like(q),
                func.lower(PO.client_name).like(q),
                func.lower(PO.filename).like(q),
                func.lower(func.cast(PO.parsed_data, str)).like(q),
            )
        )
        .order_by(PO.created_at.desc())
        .limit(limit)
        .all()
    )


def ingest_files(db: Session, file_metas: List[Dict]) -> Dict[str, object]:
    summary = {"ingested": 0, "duplicates": 0, "errors": []}
    for file_meta in file_metas:
        added, error = ingest_file(db, file_meta)
        if added:
            summary["ingested"] += 1
        elif error:
            summary["errors"].append({
                "file_id": file_meta.get("file_id"),
                "source": file_meta.get("source"),
                "error": error,
            })
        else:
            summary["duplicates"] += 1
    return summary


def ingest_file(db: Session, file_meta: Dict) -> Tuple[bool, Optional[str]]:
    file_id = file_meta.get("file_id")
    if not file_id:
        return False, "missing file_id"

    exists = db.query(PO).filter(PO.file_id == file_id).first()
    if exists:
        return False, None

    source = file_meta.get("source")
    filename = file_meta.get("filename") or "untitled"
    mime_type = file_meta.get("mime_type")

    content: Optional[bytes] = None
    try:
        if source == "gmail":
            content = gmail_service.download_attachment(
                file_meta.get("message_id", ""), file_meta.get("attachment_id", "")
            )
        elif source == "drive":
            content = drive_service.download_file(file_id)
        else:
            return False, f"unknown source {source}"
    except RuntimeError as exc:
        return False, str(exc)

    if not content:
        return False, "empty file content"

    try:
        parsed = parser_service.parse_document(content, filename, mime_type=mime_type)
    except Exception as exc:  # pragma: no cover - parsing edge cases
        return False, f"parse failure: {exc}"

    po = PO(
        po_number=parsed.get("po_number"),
        date=_safe_parse_date(parsed.get("date")),
        client_name=parsed.get("client"),
        total_value=_safe_float(parsed.get("total_value")),
        source=source,
        file_id=file_id,
        filename=filename,
        parsed_data=parsed,
    )

    db.add(po)
    return True, None


def _safe_parse_date(value) -> Optional[date]:
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    try:
        return date_parser.parse(str(value)).date()
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
