"""Very small cookie-session auth for local dashboard access."""

from __future__ import annotations

from secrets import token_urlsafe
from typing import Any

from fastapi import HTTPException, Request, Response, WebSocket, status

from app.config import get_settings

_sessions: dict[str, dict[str, Any]] = {}


def _cookie_name() -> str:
    return get_settings().session_cookie_name


def _auth_enabled() -> bool:
    return get_settings().auth_enabled


def _user_payload() -> dict[str, str]:
    settings = get_settings()
    return {"username": settings.auth_username}


def authenticate(username: str, password: str) -> dict[str, str] | None:
    settings = get_settings()
    if username == settings.auth_username and password == settings.auth_password:
        return _user_payload()
    return None


def create_session(response: Response, user: dict[str, str]) -> str:
    session_id = token_urlsafe(32)
    _sessions[session_id] = user
    response.set_cookie(
        key=_cookie_name(),
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 12,
        path="/",
    )
    return session_id


def clear_session(response: Response, request: Request | None = None, session_id: str | None = None) -> None:
    token = session_id or (request.cookies.get(_cookie_name()) if request else None)
    if token:
        _sessions.pop(token, None)
    response.delete_cookie(key=_cookie_name(), path="/")


def get_current_user_from_request(request: Request) -> dict[str, str]:
    if not _auth_enabled():
        return _user_payload()

    session_id = request.cookies.get(_cookie_name())
    user = _sessions.get(session_id or "")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def get_current_user_from_websocket(ws: WebSocket) -> dict[str, str]:
    if not _auth_enabled():
        return _user_payload()

    session_id = ws.cookies.get(_cookie_name())
    user = _sessions.get(session_id or "")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user
