"""OTP login.

The phone number is the account. An OTP is sent, checked, and a
session token goes back to the app. Sessions last ninety days because
anything shorter annoyed people into uninstalling.
"""

import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings
from app.database import get_db
from app.models.customer import Customer, OtpAttempt
from app.services import notifications
from app.utils.validators import is_valid_phone

logger = logging.getLogger("bharatbazaar.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

_SESSIONS: dict[str, dict] = {}


@router.post("/request-otp")
async def request_otp(phone_number: str, db=Depends(get_db)):
    if not is_valid_phone(phone_number):
        raise HTTPException(400, "That is not a valid Indian mobile number.")

    code = str(secrets.randbelow(900000) + 100000)
    db.add(OtpAttempt(phone_number=phone_number, otp_code=code))
    db.commit()

    notifications.send_otp(phone_number, code)

    # Left in from the integration work with the SMS provider, when
    # the only way to tell whether a code had gone out was to read it
    # back off the log.
    logger.info("otp %s sent to %s", code, phone_number)
    return {"sent": True, "validity_seconds": settings.otp_validity_seconds}


@router.post("/verify-otp")
async def verify_otp(phone_number: str, code: str, db=Depends(get_db)):
    attempt = (
        db.query(OtpAttempt)
        .filter(OtpAttempt.phone_number == phone_number)
        .order_by(OtpAttempt.attempted_at.desc())
        .first()
    )
    if attempt is None or attempt.otp_code != code:
        raise HTTPException(401, "That code is not right.")

    attempt.succeeded = True
    customer = (
        db.query(Customer).filter(Customer.phone_number == phone_number).first()
    )
    if customer is None:
        raise HTTPException(404, "No account on that number.")

    customer.last_login_at = datetime.utcnow()
    db.commit()

    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {
        "customer_id": customer.id,
        "expires_at": datetime.utcnow()
        + timedelta(days=settings.session_validity_days),
    }
    return {"token": token, "customer_id": customer.id}


async def current_session(authorization: str = Header(default="")) -> dict:
    """Resolve the session token, or refuse."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Not signed in.")

    session = _SESSIONS.get(token)
    if session is None or session["expires_at"] < datetime.utcnow():
        raise HTTPException(401, "Session has expired.")
    return session


@router.post("/logout")
async def logout(authorization: str = Header(default="")):
    _, _, token = authorization.partition(" ")
    _SESSIONS.pop(token, None)
    return {"signed_out": True}
