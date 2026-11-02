"""Support tickets, returns and abuse reports.

Support is a product function here. There is no separate intake for a
privacy complaint, no named officer on the response, and no deadline
attached to a ticket, because the queue was built to the service level
the operations team agreed rather than to anything statutory.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import current_session
from app.database import get_db
from app.models.order import Order
from app.models.support import AbuseReport, ReturnRequest, SupportTicket
from app.services import notifications

logger = logging.getLogger("bharatbazaar.support")

router = APIRouter(prefix="/api/support", tags=["support"])

CATEGORIES = (
    "order_not_delivered",
    "wrong_item",
    "damaged_item",
    "refund_not_received",
    "account_issue",
    "other",
)


@router.post("/tickets")
async def raise_ticket(
    subject: str,
    body: str,
    category: str = "other",
    order_id: int = 0,
    session=Depends(current_session),
    db=Depends(get_db),
):
    if category not in CATEGORIES:
        category = "other"

    ticket = SupportTicket(
        customer_id=session["customer_id"],
        order_id=order_id or None,
        subject=subject,
        category=category,
        body=body,
    )
    db.add(ticket)
    db.commit()
    return {"ticket_id": ticket.id, "status": ticket.status}


@router.get("/tickets")
async def my_tickets(session=Depends(current_session), db=Depends(get_db)):
    rows = (
        db.query(SupportTicket)
        .filter(SupportTicket.customer_id == session["customer_id"])
        .order_by(SupportTicket.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "subject": r.subject,
            "category": r.category,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/tickets/{ticket_id}/chat")
async def append_chat(
    ticket_id: int,
    message: str,
    session=Depends(current_session),
    db=Depends(get_db),
):
    """Append to the stored transcript.

    Customers paste order numbers, phone numbers and sometimes card
    details into this box, and all of it is kept on the ticket.
    """
    ticket = (
        db.query(SupportTicket)
        .filter(
            SupportTicket.id == ticket_id,
            SupportTicket.customer_id == session["customer_id"],
        )
        .first()
    )
    if ticket is None:
        raise HTTPException(404, "No such ticket.")

    ticket.chat_transcript = (ticket.chat_transcript or "") + "\n" + message
    db.commit()
    return {"appended": True}


@router.post("/returns")
async def request_return(
    order_id: int,
    order_item_id: int,
    reason: str,
    pickup_phone: str,
    pickup_address: str,
    refund_upi_id: str = "",
    comments: str = "",
    session=Depends(current_session),
    db=Depends(get_db),
):
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.customer_id == session["customer_id"])
        .first()
    )
    if order is None:
        raise HTTPException(404, "No such order.")

    request = ReturnRequest(
        order_id=order_id,
        order_item_id=order_item_id,
        reason=reason,
        comments=comments,
        pickup_address=pickup_address,
        pickup_phone=pickup_phone,
        refund_upi_id=refund_upi_id or None,
    )
    db.add(request)
    db.commit()

    logger.info(
        "return %s raised for order %s, pickup %s at %s, refund to %s",
        request.id, order.order_number, pickup_phone, pickup_address, refund_upi_id,
    )
    notifications.send_refund_notice(order, request.refund_amount or 0)
    return {"return_id": request.id, "status": request.status}


@router.post("/report")
async def report_abuse(
    target_type: str,
    target_id: int,
    reason: str,
    details: str = "",
    session=Depends(current_session),
    db=Depends(get_db),
):
    report = AbuseReport(
        reporter_customer_id=session["customer_id"],
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        details=details,
    )
    db.add(report)
    db.commit()
    return {"report_id": report.id}
