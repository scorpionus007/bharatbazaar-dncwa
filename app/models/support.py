"""Customer support tickets and returns.

Support is a product function here rather than a statutory one. There
is no separate route for a privacy complaint, no named officer and no
clock on a response, because nobody asked for one.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)

from app.database import Base


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))

    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(32))
    status = Column(String(24), default="open")

    # Whatever the customer pasted into the chat box, which in practice
    # is often an order number, a phone number and a card last four.
    chat_transcript = Column(Text)

    assigned_agent = Column(String(120))
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)

    reason = Column(String(64), nullable=False)
    comments = Column(Text)
    pickup_address = Column(Text, nullable=False)
    pickup_phone = Column(String(15), nullable=False)

    refund_amount = Column(Numeric(10, 2))
    refund_upi_id = Column(String(120))
    refund_bank_account = Column(String(20))

    status = Column(String(24), default="requested")
    requested_at = Column(DateTime, default=datetime.utcnow)


class AbuseReport(Base):
    """A report against a review or a seller."""

    __tablename__ = "abuse_reports"

    id = Column(Integer, primary_key=True)
    reporter_customer_id = Column(Integer, ForeignKey("customers.id"))
    target_type = Column(String(24), nullable=False)
    target_id = Column(Integer, nullable=False)

    reason = Column(String(64))
    details = Column(Text)
    is_actioned = Column(Boolean, default=False)
    reported_at = Column(DateTime, default=datetime.utcnow)
