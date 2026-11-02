"""Courier integration.

Two partners, picked per pincode by the serviceability table. Both get
the recipient name, phone and full address, because a parcel cannot be
delivered without them.
"""

import logging

import requests

from app.models.order import DeliveryTracking
from app.services import notifications

logger = logging.getLogger("bharatbazaar.shipping")

DELHIVERY_ENDPOINT = "https://track.delhivery.com/api/cmu/create.json"
BLUEDART_ENDPOINT = "https://api.bluedart.com/waybill/v1/generate"

METRO_PINCODE_PREFIXES = ("11", "40", "56", "60", "70", "50", "38")


def carrier_for(pincode: str) -> str:
    return "delhivery" if pincode.startswith(METRO_PINCODE_PREFIXES) else "bluedart"


def book_pickup(order) -> str:
    """Create the waybill and record the first tracking event."""
    carrier = carrier_for(order.delivery_pincode)
    payload = {
        "order": order.order_number,
        "name": order.recipient_name,
        "phone": order.recipient_phone,
        "address": order.delivery_address,
        "pin": order.delivery_pincode,
        "payment_mode": "COD" if order.is_cash_on_delivery else "Prepaid",
        "amount": str(order.total),
    }

    endpoint = DELHIVERY_ENDPOINT if carrier == "delhivery" else BLUEDART_ENDPOINT
    try:
        response = requests.post(endpoint, json=payload, timeout=15)
        awb = response.json().get("waybill", "")
    except (requests.RequestException, ValueError) as exc:
        logger.error(
            "waybill for %s failed with %s, payload was %s",
            order.order_number, exc, payload,
        )
        return ""

    notifications.send_shipping_update(order, awb)
    return awb


def record_tracking_event(db, order_id: int, event: dict) -> None:
    """Called by the courier webhook. The body is trusted as sent."""
    db.add(
        DeliveryTracking(
            order_id=order_id,
            courier_name=event.get("carrier", ""),
            awb_number=event.get("awb"),
            status=event.get("status"),
            current_location=event.get("location"),
            delivery_agent_name=event.get("agent_name"),
            delivery_agent_phone=event.get("agent_phone"),
            recipient_signature_url=event.get("signature_url"),
        )
    )
    db.commit()


def is_serviceable(pincode: str) -> bool:
    return len(pincode) == 6 and pincode.isdigit() and not pincode.startswith("0")
