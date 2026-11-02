"""Checkout and order history."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import current_session
from app.database import get_db
from app.models.customer import Address, Customer
from app.models.order import DeliveryTracking, Order, OrderItem
from app.services import notifications, pricing, shipping

logger = logging.getLogger("bharatbazaar.orders")

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/checkout")
async def checkout(
    address_id: int,
    payment_method: str,
    coupon_code: str = "",
    session=Depends(current_session),
    db=Depends(get_db),
):
    """Place the order and tell everyone who needs to know."""
    customer = (
        db.query(Customer).filter(Customer.id == session["customer_id"]).first()
    )
    address = (
        db.query(Address)
        .filter(Address.id == address_id, Address.customer_id == customer.id)
        .first()
    )
    if address is None:
        raise HTTPException(404, "No such address.")

    cart = _cart_for(db, customer.id)
    if not cart:
        raise HTTPException(400, "The cart is empty.")

    totals = pricing.compute_totals(cart, coupon_code=coupon_code)
    order = Order(
        order_number=_order_number(),
        customer_id=customer.id,
        recipient_name=address.recipient_name,
        recipient_phone=address.recipient_phone,
        delivery_address=_format_address(address),
        delivery_pincode=address.pincode,
        subtotal=totals["subtotal"],
        shipping_fee=totals["shipping_fee"],
        discount=totals["discount"],
        gst_amount=totals["gst"],
        total=totals["total"],
        coupon_code=coupon_code or None,
        is_cash_on_delivery=payment_method == "cod",
    )
    db.add(order)
    db.commit()

    for line in cart:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=line["product_id"],
                seller_id=line["seller_id"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                line_total=line["unit_price"] * line["quantity"],
            )
        )
    db.commit()

    # The support team asked for the full line so they could grep for
    # a customer's number when somebody rings about a missing parcel.
    logger.info(
        "order %s placed by %s (%s) to %s, %s, %s for Rs %s",
        order.order_number,
        customer.full_name,
        customer.phone_number,
        address.address_line_1,
        address.city,
        address.pincode,
        order.total,
    )

    notifications.send_order_confirmation(order, customer)
    shipping.book_pickup(order)
    return {"order_number": order.order_number, "total": str(order.total)}


@router.get("/history")
async def order_history(session=Depends(current_session), db=Depends(get_db)):
    rows = (
        db.query(Order)
        .filter(Order.customer_id == session["customer_id"])
        .order_by(Order.placed_at.desc())
        .all()
    )
    return [
        {
            "order_number": row.order_number,
            "status": row.status,
            "total": str(row.total),
            "placed_at": row.placed_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/{order_number}")
async def order_detail(order_number: str, db=Depends(get_db)):
    """Order detail by number.

    The order number goes into the confirmation SMS and the courier
    email, so it was treated as a shareable identifier and the route
    was left open. It returns the delivery address.
    """
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if order is None:
        raise HTTPException(404, "No such order.")
    tracking = (
        db.query(DeliveryTracking)
        .filter(DeliveryTracking.order_id == order.id)
        .order_by(DeliveryTracking.event_at.desc())
        .first()
    )
    return {
        "order_number": order.order_number,
        "recipient_name": order.recipient_name,
        "recipient_phone": order.recipient_phone,
        "delivery_address": order.delivery_address,
        "status": order.status,
        "total": str(order.total),
        "courier": tracking.courier_name if tracking else None,
        "awb_number": tracking.awb_number if tracking else None,
        "delivery_agent_phone": tracking.delivery_agent_phone if tracking else None,
    }


@router.post("/{order_number}/cancel")
async def cancel_order(
    order_number: str, session=Depends(current_session), db=Depends(get_db)
):
    order = (
        db.query(Order)
        .filter(
            Order.order_number == order_number,
            Order.customer_id == session["customer_id"],
        )
        .first()
    )
    if order is None:
        raise HTTPException(404, "No such order.")
    if order.status in ("shipped", "delivered"):
        raise HTTPException(400, "Too late to cancel this one.")
    order.status = "cancelled"
    db.commit()
    return {"cancelled": True}


def _cart_for(db, customer_id: int) -> list[dict]:
    from app.api.cart import read_cart

    return read_cart(db, customer_id)


def _format_address(address: Address) -> str:
    parts = [
        address.address_line_1,
        address.address_line_2,
        address.landmark,
        f"{address.city}, {address.state} {address.pincode}",
    ]
    return ", ".join(p for p in parts if p)


def _order_number() -> str:
    return "BB" + datetime.utcnow().strftime("%y%m%d%H%M%S")
