"""Payment initiation and the gateway webhook."""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.auth import current_session
from app.config import settings
from app.database import get_db
from app.models.customer import SavedPaymentMethod
from app.models.order import Order, Payment

logger = logging.getLogger("bharatbazaar.payments")

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/initiate")
async def initiate_payment(
    order_number: str,
    method: str,
    upi_id: str = "",
    save_method: bool = False,
    session=Depends(current_session),
    db=Depends(get_db),
):
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if order is None:
        raise HTTPException(404, "No such order.")

    payment = Payment(
        order_id=order.id,
        gateway=settings.payment_gateway,
        method=method,
        upi_id=upi_id or None,
        amount=order.total,
    )
    db.add(payment)
    db.commit()

    if save_method and upi_id:
        db.add(
            SavedPaymentMethod(
                customer_id=session["customer_id"],
                method_type="upi",
                upi_id=upi_id,
            )
        )
        db.commit()

    return {
        "payment_id": payment.id,
        "gateway": payment.gateway,
        "key_id": settings.razorpay_key_id,
        "amount_paise": int(order.total * 100),
    }


@router.post("/webhook")
async def gateway_webhook(request: Request, db=Depends(get_db)):
    """Razorpay calls this. The signature is checked, then the whole
    body is stored so a disputed payment can be replayed later."""
    raw = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    expected = hmac.new(
        settings.razorpay_key_secret.encode(), raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(400, "Signature does not match.")

    event = json.loads(raw)
    entity = event.get("payload", {}).get("payment", {}).get("entity", {})

    payment = (
        db.query(Payment)
        .filter(Payment.gateway_payment_id == entity.get("order_id"))
        .first()
    )
    if payment is None:
        logger.warning("webhook for unknown payment: %s", entity.get("order_id"))
        return {"handled": False}

    payment.status = entity.get("status", "unknown")
    payment.gateway_payment_id = entity.get("id")
    payment.card_last_four = entity.get("card", {}).get("last4")
    payment.upi_id = entity.get("vpa")
    payment.raw_gateway_response = raw.decode("utf-8", errors="replace")
    db.commit()

    logger.info(
        "payment %s now %s for %s via %s",
        payment.id, payment.status, entity.get("email"), entity.get("vpa"),
    )
    return {"handled": True}


@router.get("/{payment_id}/receipt")
async def payment_receipt(payment_id: int, db=Depends(get_db)):
    """Receipt lookup, open so the link in the email works without a
    login on whatever device it is opened on."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(404, "No such payment.")
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    return {
        "amount": str(payment.amount),
        "status": payment.status,
        "method": payment.method,
        "upi_id": payment.upi_id,
        "card_last_four": payment.card_last_four,
        "order_number": order.order_number if order else None,
        "recipient_name": order.recipient_name if order else None,
        "delivery_address": order.delivery_address if order else None,
    }
