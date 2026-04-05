"""Very small cookie-session auth for local dashboard access."""

from __future__ import annotations

import json
import time
from secrets import token_urlsafe
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import HTTPException, Request, Response, WebSocket, status

try:
    import jwt as pyjwt
    from jwt.exceptions import InvalidTokenError
except Exception:  # pragma: no cover - environment-specific fallback
    pyjwt = None

    class InvalidTokenError(Exception):
        pass

from app.config import get_settings

_sessions: dict[str, dict[str, Any]] = {}
_jwks_cache: dict[str, Any] = {"keys": {}, "expires_at": 0.0}


def _cookie_name() -> str:
    return get_settings().session_cookie_name


def _auth_enabled() -> bool:
    return get_settings().auth_enabled


def _user_payload() -> dict[str, str]:
    settings = get_settings()
    return {"username": settings.auth_username}


def _supabase_auth_enabled() -> bool:
    settings = get_settings()
    return bool(
        settings.supabase_auth_enabled
        and settings.supabase_url.strip()
        and settings.supabase_anon_key.strip()
    )


def _supabase_required_for_auth() -> bool:
    return _auth_enabled()


def _get_bearer_token_from_request(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    return token or None


def _get_bearer_token_from_websocket(ws: WebSocket) -> str | None:
    header = ws.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
        if token:
            return token

    query_token = ws.query_params.get("access_token", "").strip()
    return query_token or None


def _fetch_supabase_jwks() -> dict[str, Any]:
    settings = get_settings()
    base_url = settings.supabase_url.strip().rstrip("/")
    url = f"{base_url}/auth/v1/.well-known/jwks.json"
    req = urllib_request.Request(url, method="GET")
    with urllib_request.urlopen(req, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
        keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(keys, list):
            return {}
        key_map: dict[str, Any] = {}
        for item in keys:
            if not isinstance(item, dict):
                continue
            kid = item.get("kid")
            if isinstance(kid, str) and kid:
                key_map[kid] = item
        return key_map


def _get_cached_jwks() -> dict[str, Any]:
    now = time.time()
    if now < float(_jwks_cache.get("expires_at", 0.0)) and isinstance(_jwks_cache.get("keys"), dict):
        return _jwks_cache["keys"]

    keys = _fetch_supabase_jwks()
    _jwks_cache["keys"] = keys
    _jwks_cache["expires_at"] = now + 300
    return keys


def _decode_supabase_access_token(token: str) -> dict[str, Any] | None:
    if pyjwt is None:
        return None

    settings = get_settings()
    base_url = settings.supabase_url.strip().rstrip("/")
    issuer = f"{base_url}/auth/v1"

    try:
        unverified = pyjwt.get_unverified_header(token)
    except InvalidTokenError:
        return None

    kid = unverified.get("kid") if isinstance(unverified, dict) else None
    alg = unverified.get("alg") if isinstance(unverified, dict) else None
    if not isinstance(kid, str) or not kid:
        return None
    if not isinstance(alg, str) or not alg:
        return None

    try:
        keys = _get_cached_jwks()
    except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    jwk = keys.get(kid)
    if not isinstance(jwk, dict):
        return None

    try:
        public_key = pyjwt.PyJWK.from_dict(jwk).key
        claims = pyjwt.decode(
            token,
            public_key,
            algorithms=[alg],
            issuer=issuer,
            options={"verify_aud": False},
        )
    except (InvalidTokenError, AttributeError):
        return None

    return claims if isinstance(claims, dict) else None


def _supabase_user_from_token(token: str) -> dict[str, str] | None:
    claims = _decode_supabase_access_token(token)
    if not claims:
        return None

    user_email = claims.get("email")
    if isinstance(user_email, str) and user_email:
        return {"username": user_email}

    user_sub = claims.get("sub")
    if isinstance(user_sub, str) and user_sub:
        return {"username": user_sub}

    return None


def _authenticate_via_supabase(email: str, password: str) -> dict[str, str] | None:
    settings = get_settings()
    base_url = settings.supabase_url.strip().rstrip("/")
    anon_key = settings.supabase_anon_key.strip()
    if not base_url or not anon_key:
        return None

    url = f"{base_url}/auth/v1/token?grant_type=password"
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "apikey": anon_key,
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            user_data = data.get("user") if isinstance(data, dict) else None
            if isinstance(user_data, dict):
                user_email = user_data.get("email")
                if isinstance(user_email, str) and user_email:
                    return {"username": user_email}
            return {"username": email}
    except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def authenticate(username: str, password: str) -> dict[str, str] | None:
    if _supabase_required_for_auth() and not _supabase_auth_enabled():
        return None

    return _authenticate_via_supabase(username, password)


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

    if not _supabase_auth_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase auth is not configured")

    token = _get_bearer_token_from_request(request)
    user = _supabase_user_from_token(token) if token else None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def get_current_user_from_websocket(ws: WebSocket) -> dict[str, str]:
    if not _auth_enabled():
        return _user_payload()

    if not _supabase_auth_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase auth is not configured")

    token = _get_bearer_token_from_websocket(ws)
    user = _supabase_user_from_token(token) if token else None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user
