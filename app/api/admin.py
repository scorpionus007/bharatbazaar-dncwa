"""Internal operations console.

Mounted on the same application as the storefront and protected by
not being linked from anywhere. The operations team reaches it over
the office VPN, which was the reasoning at the time: if you cannot get
to the host you cannot get to the route.
"""

import csv
import io
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.models.customer import Customer, OtpAttempt
from app.models.order import Order
from app.models.seller import Seller

logger = logging.getLogger("bharatbazaar.admin")

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/customers")
async def list_all_customers(limit: int = 500, db=Depends(get_db)):
    """Everybody, with contact details, for the ops console table."""
    rows = db.query(Customer).limit(limit).all()
    return [
        {
            "id": row.id,
            "full_name": row.full_name,
            "phone_number": row.phone_number,
            "email_address": row.email_address,
            "date_of_birth": row.date_of_birth,
            "wallet_balance": str(row.wallet_balance),
            "marketing_opt_in": row.marketing_opt_in,
        }
        for row in rows
    ]


@router.get("/customers/export.csv")
async def export_customers(db=Depends(get_db)):
    """The marketing team asked for this and it was faster to build
    than to argue about."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["id", "full_name", "phone_number", "email_address", "city", "pincode"]
    )
    for row in db.query(Customer).all():
        default_address = next(
            (a for a in row.addresses if a.is_default), None
        )
        writer.writerow(
            [
                row.id,
                row.full_name,
                row.phone_number,
                row.email_address or "",
                default_address.city if default_address else "",
                default_address.pincode if default_address else "",
            ]
        )
    buffer.seek(0)
    logger.info("exported %s customer rows to csv", db.query(Customer).count())
    return StreamingResponse(buffer, media_type="text/csv")


@router.get("/sellers/kyc")
async def seller_kyc_review(db=Depends(get_db)):
    """The KYC queue, with the documents attached."""
    rows = db.query(Seller).filter(Seller.is_active.is_(True)).all()
    return [
        {
            "id": row.id,
            "legal_name": row.legal_name,
            "pan_number": row.pan_number,
            "aadhaar_number": row.aadhaar_number,
            "gst_number": row.gst_number,
            "bank_account_number": row.bank_account_number,
            "bank_ifsc": row.bank_ifsc,
        }
        for row in rows
    ]


@router.get("/otp-log")
async def otp_log(phone_number: str = "", limit: int = 200, db=Depends(get_db)):
    """Fraud investigation view over the OTP history."""
    query = db.query(OtpAttempt)
    if phone_number:
        query = query.filter(OtpAttempt.phone_number == phone_number)
    rows = query.order_by(OtpAttempt.attempted_at.desc()).limit(limit).all()
    return [
        {
            "phone_number": row.phone_number,
            "otp_code": row.otp_code,
            "ip_address": row.ip_address,
            "device_id": row.device_id,
            "succeeded": row.succeeded,
            "attempted_at": row.attempted_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/orders/search")
async def search_orders(phone_number: str = "", db=Depends(get_db)):
    """Support looks up an order by the caller's phone number."""
    query = db.query(Order)
    if phone_number:
        query = query.filter(Order.recipient_phone == phone_number)
    rows = query.limit(100).all()
    logger.info("order search for %s returned %s rows", phone_number, len(rows))
    return [
        {
            "order_number": row.order_number,
            "recipient_name": row.recipient_name,
            "recipient_phone": row.recipient_phone,
            "delivery_address": row.delivery_address,
            "total": str(row.total),
            "status": row.status,
        }
        for row in rows
    ]
