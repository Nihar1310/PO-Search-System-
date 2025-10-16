from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PO
from ..services.search_service import search_pos


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
        orm_mode = True


@router.post("/search", response_model=List[POSummary])
def search_endpoint(payload: SearchRequest, db: Session = Depends(get_db)):
    results: List[PO] = search_pos(db, payload.query)
    return results

