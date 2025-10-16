from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from ..config import get_settings


settings = get_settings()
SCOPES = [scope.strip() for scope in settings.GOOGLE_SCOPES.split(",") if scope.strip()]
TOKEN_PATH = Path(settings.GOOGLE_TOKEN_PATH)


def _build_flow(state: Optional[str] = None) -> Flow:
    redirect_uri = settings.REDIRECT_URI
    if settings.GOOGLE_CLIENT_SECRETS_FILE:
        flow = Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
    else:
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)

    if state:
        flow.state = state
    return flow


def generate_auth_url(state: Optional[str] = None) -> Tuple[str, str]:
    flow = _build_flow(state)
    authorization_url, new_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url, new_state


def exchange_code(code: str, state: Optional[str] = None) -> Credentials:
    flow = _build_flow(state)
    flow.fetch_token(code=code)
    credentials = flow.credentials
    store_credentials(credentials)
    return credentials


def store_credentials(credentials: Credentials) -> None:
    TOKEN_PATH.write_text(credentials.to_json())


def load_credentials() -> Optional[Credentials]:
    if not TOKEN_PATH.exists():
        return None
    data = json.loads(TOKEN_PATH.read_text())
    return Credentials.from_authorized_user_info(data, scopes=SCOPES)


def get_credentials(auto_refresh: bool = True) -> Optional[Credentials]:
    credentials = load_credentials()
    if not credentials:
        return None

    if auto_refresh and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        store_credentials(credentials)
    return credentials


def credentials_available() -> bool:
    credentials = get_credentials(auto_refresh=False)
    return credentials is not None


def clear_credentials() -> None:
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()

