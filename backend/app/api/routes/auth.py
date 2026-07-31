"""
Authentication API routes.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.schemas.models import LoginRequest, TokenResponse
from app.utils.auth import create_access_token, decode_access_token, verify_credentials

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT token",
)
async def login(payload: LoginRequest) -> TokenResponse:
    """
    Authenticate with username and password.
    Returns a JWT bearer token valid for `TOKEN_EXPIRE_HOURS`.
    """
    if not verify_credentials(payload.username, payload.password):
        logger.warning(f"Failed login attempt for username: {payload.username!r}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = create_access_token(subject=payload.username)
    logger.info(f"Successful login for: {payload.username}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.token_expire_hours * 3600,
    )


@router.get("/auth/me", summary="Verify current token and return username")
async def me(request: Request, credentials: HTTPAuthorizationCredentials = security):
    """Validate bearer token and return the authenticated username."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
        )

    username = decode_access_token(credentials.credentials)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    return {"username": username}


def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> str:
    """
    Dependency — extract and validate the authenticated user from the JWT.
    Raise 401 if missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
        )
    username = decode_access_token(credentials.credentials)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    return username
