import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import PO
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
    payload = {
        "type": "po-auth-success",
        "status": "connected",
        "scopes": credentials.scopes,
        "tokenPath": str(auth.TOKEN_PATH),
        "state": state,
    }

    scopes_list = "".join(f"<li>{scope}</li>" for scope in credentials.scopes or [])
    html_content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Google Connected</title>
  <style>
    :root {{
      color-scheme: light;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #eef2ff, #f8fafc);
      color: #0f172a;
    }}
    .card {{
      width: min(420px, 90vw);
      padding: 32px;
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.92);
      box-shadow: 0 20px 45px rgba(15, 23, 42, 0.1);
      text-align: center;
      border: 1px solid rgba(148, 163, 184, 0.2);
      backdrop-filter: blur(16px);
    }}
    h1 {{
      font-size: 1.5rem;
      margin-bottom: 0.75rem;
    }}
    p {{
      margin: 0.5rem 0 1.25rem;
      color: #475569;
      line-height: 1.5;
    }}
    ul {{
      text-align: left;
      margin: 0 auto 1.5rem;
      padding: 0;
      list-style: none;
      max-width: 320px;
      color: #334155;
    }}
    li {{
      padding-left: 1.25rem;
      position: relative;
      margin-bottom: 0.75rem;
    }}
    li::before {{
      content: '✓';
      color: #2563eb;
      position: absolute;
      left: 0;
      top: 0;
    }}
    button {{
      padding: 0.7rem 1.6rem;
      border-radius: 999px;
      border: none;
      font-weight: 600;
      background: linear-gradient(135deg, #3b82f6, #6366f1);
      color: white;
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    button:hover {{
      transform: translateY(-1px);
      box-shadow: 0 12px 24px rgba(79, 70, 229, 0.24);
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      border-radius: 999px;
      padding: 0.4rem 0.9rem;
      font-size: 0.75rem;
      font-weight: 600;
      background: rgba(245, 245, 255, 0.9);
      color: #4338ca;
      margin-bottom: 1rem;
    }}
  </style>
</head>
<body>
  <div class=\"card\">
    <div class=\"badge\">Google Connected</div>
    <h1>You're all set!</h1>
    <p>We securely stored your access token. You can return to PO Search &amp; Parsing and refresh the status.</p>
    {f"<ul>{scopes_list}</ul>" if scopes_list else ""}
    <button id=\"close-btn\" type=\"button\">Close this window</button>
  </div>
  <script>
    const message = {json.dumps(payload)};
    const closeWindow = () => {{
      window.close();
    }};
    if (window.opener && !window.opener.closed) {{
      try {{
        window.opener.postMessage(message, '*');
      }} catch (err) {{
        console.warn('Failed to notify opener', err);
      }}
      setTimeout(closeWindow, 1600);
    }}
    const closeBtn = document.getElementById('close-btn');
    if (closeBtn) {{
      closeBtn.addEventListener('click', closeWindow);
    }}
  </script>
</body>
</html>"""

    return HTMLResponse(content=html_content)


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
def analytics(db: Session = Depends(get_db)):
    total_pos = db.query(func.count(PO.id)).scalar() or 0
    total_value = db.query(func.coalesce(func.sum(PO.total_value), 0)).scalar() or 0.0
    latest_created = db.query(func.max(PO.created_at)).scalar()

    average_value = float(total_value) / total_pos if total_pos else 0.0

    month_expr = func.strftime("%Y-%m", func.coalesce(PO.date, func.date(PO.created_at)))
    monthly_rows = (
        db.query(
            month_expr.label("month"),
            func.count(PO.id).label("po_count"),
            func.coalesce(func.sum(PO.total_value), 0).label("total_value"),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly_value = [
        {
            "month": row.month,
            "po_count": row.po_count,
            "total_value": float(row.total_value or 0),
        }
        for row in monthly_rows
        if row.month is not None
    ]

    client_name_expr = func.coalesce(func.nullif(func.trim(PO.client_name), ""), "Unknown")
    top_clients_rows = (
        db.query(
            client_name_expr.label("client_name"),
            func.count(PO.id).label("po_count"),
            func.coalesce(func.sum(PO.total_value), 0).label("total_value"),
        )
        .group_by("client_name")
        .order_by(func.coalesce(func.sum(PO.total_value), 0).desc())
        .limit(5)
        .all()
    )
    top_clients = [
        {
            "client_name": row.client_name,
            "po_count": row.po_count,
            "total_value": float(row.total_value or 0),
        }
        for row in top_clients_rows
    ]

    source_rows = (
        db.query(
            func.coalesce(func.nullif(func.trim(PO.source), ""), "unknown").label("source"),
            func.count(PO.id).label("po_count"),
            func.coalesce(func.sum(PO.total_value), 0).label("total_value"),
        )
        .group_by("source")
        .order_by("source")
        .all()
    )
    source_breakdown = [
        {
            "source": row.source,
            "po_count": row.po_count,
            "total_value": float(row.total_value or 0),
        }
        for row in source_rows
    ]

    recent_pos = (
        db.query(PO.id, PO.po_number, PO.client_name, PO.total_value, PO.created_at)
        .order_by(PO.created_at.desc())
        .limit(5)
        .all()
    )
    recent_activity = [
        {
            "id": row.id,
            "po_number": row.po_number,
            "client_name": row.client_name,
            "total_value": float(row.total_value or 0)
            if row.total_value is not None
            else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in recent_pos
    ]

    return {
        "summary": {
            "total_pos": total_pos,
            "total_value": float(total_value or 0),
            "average_value": average_value,
            "last_ingested": latest_created.isoformat() if latest_created else None,
        },
        "monthly_value": monthly_value,
        "top_clients": top_clients,
        "source_breakdown": source_breakdown,
        "recent_activity": recent_activity,
    }
