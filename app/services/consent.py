"""Consent, s.6.

A checkbox that only gates a button is not a control: the browser is
the customer's own and anything decided there can be decided
differently. The refusal has to happen on the server.

Each purpose is separate. Agreeing to have an order delivered is not
agreeing to be marketed at, and s.6 takes consent to a purpose rather
than to the organisation.
"""

import logging

from fastapi import HTTPException

from app.models.customer import ConsentEvent, Customer

logger = logging.getLogger("bharatbazaar.consent")

NOTICE_VERSION = "2026-03-notice-v2"

PURPOSES = {
    "account": "Running your account and delivering what you order",
    "marketing": "Offers and recommendations by SMS and email",
    "personalisation": "Recommendations based on what you browse",
}


def record_consent(db, customer: Customer, *, purpose: str, granted: bool,
                   source: str = "web") -> ConsentEvent:
    """Append an event. Never update the previous one."""
    if purpose not in PURPOSES:
        raise HTTPException(400, f"Unknown purpose: {purpose}")

    event = ConsentEvent(
        customer_id=customer.id,
        purpose=purpose,
        granted=granted,
        notice_version=NOTICE_VERSION,
        source=source,
    )
    db.add(event)

    if purpose == "marketing":
        # The legacy column the old mobile build still reads.
        customer.marketing_opt_in = granted
    db.commit()

    logger.info(
        "consent %s for customer %s purpose %s",
        "granted" if granted else "withdrawn", customer.id, purpose,
    )
    return event


def has_consent(db, customer_id: int, purpose: str) -> bool:
    """The latest event for this purpose wins.

    Read from the event stream rather than from a flag, so a
    withdrawal is simply the most recent row and everything before it
    survives for the s.8(1) record.
    """
    latest = (
        db.query(ConsentEvent)
        .filter(
            ConsentEvent.customer_id == customer_id,
            ConsentEvent.purpose == purpose,
        )
        .order_by(ConsentEvent.consented_at.desc(), ConsentEvent.id.desc())
        .first()
    )
    return bool(latest and latest.granted)


def require_consent(db, customer_id: int, purpose: str) -> None:
    """Refuse the processing. Called from the service layer.

    Raised rather than silently skipped, so an absent consent shows up
    in the logs instead of looking like the feature never ran.
    """
    if not has_consent(db, customer_id, purpose):
        raise HTTPException(
            status_code=403,
            detail=(
                f"No consent recorded for {purpose}. Section 6 makes consent "
                "the lawful basis, so this processing cannot proceed."
            ),
        )


def withdraw_consent(db, customer: Customer, purpose: str) -> ConsentEvent:
    """s.6(4). Withdrawal has to be as easy as giving it was."""
    return record_consent(db, customer, purpose=purpose, granted=False)


def consent_summary(db, customer_id: int) -> list[dict]:
    """Every purpose and where it currently stands, for the privacy page."""
    return [
        {
            "purpose": purpose,
            "label": label,
            "granted": has_consent(db, customer_id, purpose),
            "notice_version": NOTICE_VERSION,
        }
        for purpose, label in PURPOSES.items()
    ]
