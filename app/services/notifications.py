"""Transactional messaging: OTP, order updates, refunds.

SMS goes through MSG91 and email through a local SMTP relay. Both are
Indian and in India, which is the only reason nobody has had to think
about where a message ends up.
"""

import logging

import requests

from app.config import settings

logger = logging.getLogger("bharatbazaar.notifications")

MSG91_ENDPOINT = "https://api.msg91.com/api/v5/flow/"

TEMPLATES = {
    "otp": "otp_login_v3",
    "order_placed": "order_confirmation_v7",
    "order_shipped": "order_shipped_v4",
    "refund_initiated": "refund_initiated_v2",
}


def send_otp(phone_number: str, code: str) -> None:
    _send_sms(phone_number, TEMPLATES["otp"], {"otp": code})


def send_order_confirmation(order, customer) -> None:
    _send_sms(
        customer.phone_number,
        TEMPLATES["order_placed"],
        {
            "name": customer.full_name,
            "order_number": order.order_number,
            "amount": str(order.total),
        },
    )


def send_shipping_update(order, awb_number: str) -> None:
    _send_sms(
        order.recipient_phone,
        TEMPLATES["order_shipped"],
        {"order_number": order.order_number, "awb": awb_number},
    )


def send_refund_notice(order, amount) -> None:
    _send_sms(
        order.recipient_phone,
        TEMPLATES["refund_initiated"],
        {"order_number": order.order_number, "amount": str(amount)},
    )


def _send_sms(phone_number: str, template_id: str, variables: dict) -> None:
    payload = {
        "template_id": template_id,
        "recipients": [{"mobiles": "91" + phone_number, **variables}],
    }
    try:
        response = requests.post(
            MSG91_ENDPOINT,
            json=payload,
            headers={"authkey": settings.msg91_auth_key},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        # The payload is logged on failure so the message can be sent
        # again by hand. It carries the number and the name.
        logger.error("sms to %s failed: %s payload=%s", phone_number, exc, payload)
