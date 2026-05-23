"""API key security dependency."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.settings import settings

_security = HTTPBearer(auto_error=False)


async def verify_admin_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),  # noqa: B008
) -> str:
    """Verify admin API token from Authorization header.

    Health endpoint is publicly accessible.
    """
    token = settings.admin_api_token
    if token is None:
        # No token configured — allow access in local dev
        return "local"

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if credentials.credentials != token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API token",
        )

    return credentials.credentials
