"""Telegram auth endpoints (skeleton for Wave 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import verify_admin_token

router = APIRouter(prefix="/auth", tags=["auth"])


class SendCodeResponse(BaseModel):
    status: str


class ConfirmCodeRequest(BaseModel):
    code: str


class Confirm2FARequest(BaseModel):
    password: str


@router.post("/send-code")
async def send_code(_token: str = Depends(verify_admin_token)) -> SendCodeResponse:
    # TODO: implement in BL-0202
    raise HTTPException(status_code=501, detail="Not implemented: Telegram auth not connected yet")


@router.post("/confirm-code")
async def confirm_code(
    _req: ConfirmCodeRequest,
    _token: str = Depends(verify_admin_token),
) -> SendCodeResponse:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/confirm-2fa")
async def confirm_2fa(
    _req: Confirm2FARequest,
    _token: str = Depends(verify_admin_token),
) -> SendCodeResponse:
    raise HTTPException(status_code=501, detail="Not implemented")
