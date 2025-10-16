from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PO


router = APIRouter(prefix="/api", tags=["po"])


@router.get("/po/{po_id}")
def get_po(po_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    po = db.query(PO).filter(PO.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    return {
        "id": po.id,
        "po_number": po.po_number,
        "date": po.date.isoformat() if po.date else None,
        "client_name": po.client_name,
        "total_value": po.total_value,
        "source": po.source,
        "filename": po.filename,
        "parsed_data": po.parsed_data or {},
    }


@router.get("/po/{po_id}/export")
def export_po(po_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    po = db.query(PO).filter(PO.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    # For now return the parsed JSON as-is
    return po.parsed_data or {}

