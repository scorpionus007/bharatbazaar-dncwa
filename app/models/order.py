"""Orders, payments and delivery tracking."""

from datetime import datetime, timedelta

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
from sqlalchemy.orm import relationship

from app.database import Base


class Order(Base):
    """An order.

    The delivery address is copied onto the order rather than joined,
    because the customer may edit or delete the address afterwards and
    the invoice has to keep saying where it went. The practical effect
    is a second permanent copy of the address per order.
    """

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(24), nullable=False, unique=True, index=True)
    # Nullable because the invoice outlives the account. On erasure the
    # order is kept in reduced form for as long as tax law wants it and
    # stops pointing at a person. See app/services/erasure.py.
    customer_id = Column(Integer, ForeignKey("customers.id"))

    recipient_name = Column(String(255), nullable=False)
    recipient_phone = Column(String(15), nullable=False)
    delivery_address = Column(Text, nullable=False)
    delivery_pincode = Column(String(6), nullable=False)

    subtotal = Column(Numeric(10, 2), nullable=False)
    shipping_fee = Column(Numeric(10, 2), default=0)
    discount = Column(Numeric(10, 2), default=0)
    gst_amount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)

    coupon_code = Column(String(32))
    status = Column(String(24), default="placed")
    is_cash_on_delivery = Column(Boolean, default=False)

    placed_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime)
    # Eight years, which is what section 128 of the Companies Act asks
    # of books of account. s.8(7) allows retention a law requires.
    expires_at = Column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=365 * 8), index=True
    )

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)

    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")


class Payment(Base):
    """A payment attempt against an order."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    gateway = Column(String(32), nullable=False)
    gateway_payment_id = Column(String(64), index=True)
    method = Column(String(24))
    upi_id = Column(String(120))
    card_last_four = Column(String(4))

    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(24), default="initiated")
    failure_reason = Column(Text)

    # The whole gateway callback body, stored verbatim so support can
    # replay a disputed payment. It contains the payer name, the UPI
    # handle and sometimes the card bin.
    raw_gateway_response = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=365 * 8), index=True
    )


class DeliveryTracking(Base):
    """Courier events, pushed in by the logistics partner webhook."""

    __tablename__ = "delivery_tracking"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    courier_name = Column(String(64), nullable=False)
    awb_number = Column(String(32), index=True)
    status = Column(String(32))
    current_location = Column(String(255))
    delivery_agent_name = Column(String(255))
    delivery_agent_phone = Column(String(15))
    recipient_signature_url = Column(String(512))

    event_at = Column(DateTime, default=datetime.utcnow)
    # A year. The courier keeps its own record; this copy is for the
    # tracking page and stops being useful long before that.
    expires_at = Column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=365)
    )
