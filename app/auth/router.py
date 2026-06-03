"""Auth & verification endpoints: phone OTP → session token → CNIC capture."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ratelimit import ip_rate_limit

from app.auth import otp as otp_mod
from app.auth.deps import get_current_user
from app.auth.schemas import (
    CnicSubmit,
    OtpRequest,
    OtpRequestResponse,
    OtpVerify,
    TokenResponse,
    UserOut,
)
from app.auth.sender import get_sender
from app.auth.validators import InvalidCnic, InvalidPhone, normalize_cnic, normalize_pk_phone
from app.config import get_settings
from app.db import get_session
from app.models.user import User
from app.redis_client import get_redis
from app.security import create_access_token, encrypt_phone, hash_identifier

router = APIRouter(prefix="/auth", tags=["auth"])

_s = get_settings()
_otp_request_limit = ip_rate_limit("otp_request", _s.otp_request_rate_limit, _s.otp_request_rate_window)
_otp_verify_limit = ip_rate_limit("otp_verify", _s.otp_verify_rate_limit, _s.otp_verify_rate_window)


def _service() -> otp_mod.OtpService:
    return otp_mod.OtpService(get_redis())


@router.post("/otp/request", response_model=OtpRequestResponse, dependencies=[Depends(_otp_request_limit)])
async def request_otp(body: OtpRequest) -> OtpRequestResponse:
    try:
        phone = normalize_pk_phone(body.phone)
    except InvalidPhone as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    roles = body.roles or ["tenant"]
    can_own, can_rent = "owner" in roles, "tenant" in roles

    try:
        code = await _service().request(phone, body.name, can_own, can_rent)
    except otp_mod.OtpCooldown as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))

    sender = get_sender()
    await sender.send(phone, code)

    settings = get_settings()
    # Surface the code in the response ONLY for local dev with no real channel configured.
    dev_code = code if (sender.channel == "console" and not settings.is_prod) else None
    return OtpRequestResponse(
        sent=True, channel=sender.channel, expires_in=settings.otp_ttl_seconds, dev_code=dev_code
    )


@router.post("/otp/verify", response_model=TokenResponse, dependencies=[Depends(_otp_verify_limit)])
async def verify_otp(body: OtpVerify, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    try:
        phone = normalize_pk_phone(body.phone)
    except InvalidPhone as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        pending = await _service().verify(phone, body.code)
    except otp_mod.OtpTooManyAttempts as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))
    except otp_mod.OtpInvalid as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    phone_hash = hash_identifier(phone)
    user = await session.scalar(select(User).where(User.phone_hash == phone_hash))
    if user is None:
        user = User(
            name=pending.name,
            phone_hash=phone_hash,
            phone=encrypt_phone(phone),  # encrypted at rest; revealed only on mutual consent
            can_own=pending.can_own,
            can_rent=pending.can_rent,
        )
        session.add(user)
    else:
        # Returning user: refresh name/roles from this request, keep existing account.
        if pending.name:
            user.name = pending.name
        user.phone = encrypt_phone(phone)
        user.can_own = user.can_own or pending.can_own
        user.can_rent = user.can_rent or pending.can_rent

    user.verified_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.from_user(user))


@router.post("/cnic", response_model=UserOut)
async def submit_cnic(
    body: CnicSubmit,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    try:
        cnic_digits = normalize_cnic(body.cnic)
    except InvalidCnic as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    user.cnic_hash = hash_identifier(cnic_digits)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This CNIC is already registered")
    await session.refresh(user)
    return UserOut.from_user(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_user(user)
