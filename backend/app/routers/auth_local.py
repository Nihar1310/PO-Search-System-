from __future__ import annotations

__all__ = ['get_current_user']

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import User
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

COOKIE_NAME = "po_access_token"
COOKIE_MAX_AGE = settings.APP_ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.APP_COOKIE_SECURE,
        samesite="lax",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, httponly=True, secure=settings.APP_COOKIE_SECURE, samesite="lax")


@router.post("/login", response_model=dict)
def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not user.is_active or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=settings.APP_ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"sub": user.username}, expires_delta=access_token_expires)
    _set_auth_cookie(response, token)
    return {"username": user.username}


@router.post("/logout", response_model=dict)
def logout(response: Response):
    _clear_auth_cookie(response)
    return {"status": "logged_out"}


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    from ..security import decode_access_token

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    username = payload["sub"]
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User disabled")
    return user


@router.get("/session", response_model=dict)
def session(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username}
