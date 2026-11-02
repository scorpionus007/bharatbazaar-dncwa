"""Erasure, s.12(3) and s.8(7)(b).

Deleting the customer row is the easy part. The duty is to reach the
copies: the addresses, the saved cards, the wishlist, the browsing
history and the reviews that carry the person's name.

What is deliberately kept is listed in KEPT_AFTER_ERASURE below and
shown to the customer before they confirm, because an erasure that
quietly retains things is worse than one that explains itself.
"""

import logging

from app.models.catalog import BrowsingEvent, Review, WishlistItem
from app.models.customer import (
    Address,
    ConsentEvent,
    Customer,
    Nomination,
    OtpAttempt,
    SavedPaymentMethod,
)
from app.models.order import Order
from app.services import audit

logger = logging.getLogger("bharatbazaar.erasure")

# s.8(7) allows retention where another law requires it. The invoice
# is one: the Companies Act and the GST rules both want it kept, so
# the order survives in a reduced form with the contact details
# stripped out.
KEPT_AFTER_ERASURE = (
    "Order invoices, for the period tax law requires, with the name "
    "and phone number replaced by a placeholder",
)

PLACEHOLDER_NAME = "Erased customer"
PLACEHOLDER_PHONE = "0000000000"


def erase_customer(db, customer: Customer) -> dict:
    """Erase the person and cascade to the copies."""
    customer_id = customer.id
    removed = {}

    for model, column in (
        (Address, Address.customer_id),
        (SavedPaymentMethod, SavedPaymentMethod.customer_id),
        (WishlistItem, WishlistItem.customer_id),
        (BrowsingEvent, BrowsingEvent.customer_id),
        (ConsentEvent, ConsentEvent.customer_id),
        (Nomination, Nomination.customer_id),
    ):
        rows = db.query(model).filter(column == customer_id).all()
        for row in rows:
            db.delete(row)
        removed[model.__tablename__] = len(rows)

    # The OTP log is keyed on the number, not the customer id.
    otps = (
        db.query(OtpAttempt)
        .filter(OtpAttempt.phone_number == customer.phone_number)
        .all()
    )
    for row in otps:
        db.delete(row)
    removed["otp_attempts"] = len(otps)

    # A review stays, because other shoppers relied on it, but it
    # stops carrying the reviewer's name.
    reviews = db.query(Review).filter(Review.customer_id == customer_id).all()
    for review in reviews:
        review.reviewer_display_name = PLACEHOLDER_NAME
        review.customer_id = None
    removed["reviews_anonymised"] = len(reviews)

    # s.8(7)(b). The invoice is kept because tax law requires it, with
    # the personal data on it reduced to what the invoice needs.
    orders = db.query(Order).filter(Order.customer_id == customer_id).all()
    for order in orders:
        order.recipient_name = PLACEHOLDER_NAME
        order.recipient_phone = PLACEHOLDER_PHONE
        order.delivery_address = f"{order.delivery_pincode} (address erased)"
        order.customer_id = None
    removed["orders_reduced"] = len(orders)

    audit.record_access(db, None, "erase", "customer", customer_id)
    db.delete(customer)
    db.commit()

    logger.info("erased customer %s, cascade %s", customer_id, removed)
    return {"erased": True, "cascade": removed, "kept": list(KEPT_AFTER_ERASURE)}


def export_customer(db, customer: Customer) -> dict:
    """s.11(1)(a). A summary of what is held, in one response."""
    addresses = (
        db.query(Address).filter(Address.customer_id == customer.id).all()
    )
    consents = (
        db.query(ConsentEvent)
        .filter(ConsentEvent.customer_id == customer.id)
        .order_by(ConsentEvent.consented_at)
        .all()
    )
    orders = db.query(Order).filter(Order.customer_id == customer.id).all()

    audit.record_access(db, customer.id, "export", "customer", customer.id)

    return {
        "identity": {
            "full_name": customer.full_name,
            "phone_number": customer.phone_number,
            "email_address": customer.email_address,
            "date_of_birth": customer.date_of_birth,
        },
        "addresses": [
            {
                "recipient_name": a.recipient_name,
                "address_line_1": a.address_line_1,
                "city": a.city,
                "state": a.state,
                "pincode": a.pincode,
            }
            for a in addresses
        ],
        "consents": [
            {
                "purpose": c.purpose,
                "granted": c.granted,
                "notice_version": c.notice_version,
                "consented_at": c.consented_at.isoformat(),
            }
            for c in consents
        ],
        "orders": [
            {
                "order_number": o.order_number,
                "total": str(o.total),
                "placed_at": o.placed_at.isoformat() if o.placed_at else None,
            }
            for o in orders
        ],
        "retention": {
            "account_erased_after": customer.expires_at.isoformat()
            if customer.expires_at
            else None,
        },
    }
