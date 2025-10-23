from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PO
from ..services.search_service import search_pos
from .auth_local import get_current_user


router = APIRouter(prefix="/api", tags=["search"])


class SearchRequest(BaseModel):
    query: str


class POSummary(BaseModel):
    id: int
    po_number: Optional[str] = None
    date: Optional[str] = None
    client_name: Optional[str] = None
    total_value: Optional[float] = None
    source: Optional[str] = None
    filename: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/search", response_model=List[POSummary])
def search_endpoint(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    results: List[PO] = search_pos(db, payload.query)
    # Convert PO objects to POSummary with date serialization
    return [
        POSummary(
            id=po.id,
            po_number=po.po_number,
            date=po.date.isoformat() if po.date else None,
            client_name=po.client_name,
            total_value=po.total_value,
            source=po.source,
            filename=po.filename
        )
        for po in results
    ]
