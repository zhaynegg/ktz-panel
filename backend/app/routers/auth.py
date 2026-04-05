"""Authentication endpoints for local username/password login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from app.services.auth import authenticate, clear_session, create_session, get_current_user_from_request

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(payload: LoginRequest, response: Response) -> dict:
    user = authenticate(payload.username, payload.password)
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"ok": False, "detail": "Invalid credentials"}

    create_session(response, user)
    return {"ok": True, "user": user}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    clear_session(response, request=request)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user_from_request)) -> dict:
    return {"authenticated": True, "user": user}
