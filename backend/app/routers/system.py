from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..services import sync_service
from ..utils import auth


router = APIRouter(tags=["system"])


@router.get("/auth/login")
def auth_login(state: Optional[str] = None):
    auth_url, new_state = auth.generate_auth_url(state)
    return {"auth_url": auth_url, "state": new_state}


@router.get("/auth/callback")
def auth_callback(code: str = Query(...), state: Optional[str] = None):
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")
    credentials = auth.exchange_code(code, state)
    return {
        "status": "connected",
        "scopes": credentials.scopes,
        "token_path": str(auth.TOKEN_PATH),
    }


@router.get("/auth/status")
def auth_status():
    return {"connected": auth.credentials_available()}


@router.delete("/auth/token")
def auth_disconnect():
    auth.clear_credentials()
    return {"status": "disconnected"}


class SyncRequest(BaseModel):
    gmail_query: Optional[str] = None
    drive_query: Optional[str] = None
    gmail_limit: int = 30
    drive_limit: int = 30


class SyncResponse(BaseModel):
    status: str
    summary: Dict[str, Any]


@router.post("/api/sync", response_model=SyncResponse)
def sync_sources(
    payload: SyncRequest = Body(default=SyncRequest()),
    db: Session = Depends(get_db),
):
    summary = sync_service.perform_sync(
        db,
        gmail_query=payload.gmail_query,
        drive_query=payload.drive_query,
        gmail_limit=payload.gmail_limit,
        drive_limit=payload.drive_limit,
    )

    status = "completed"
    if summary["ingested"] == 0 and summary["duplicates"] == 0:
        status = "no_changes"
    if summary["sources"]["gmail"]["error"] or summary["sources"]["drive"]["error"]:
        status = "partial" if summary["ingested"] else "failed"

    return {"status": status, "summary": summary}


@router.get("/api/analytics")
def analytics():
    # Return placeholder analytics structure
    return {
        "monthly_value": [],
        "top_clients": [],
        "total_pos": 0,
    }
