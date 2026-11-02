"""The cart, held in memory against the customer id."""

import json
import logging

from fastapi import APIRouter, Depends

from app.api.auth import current_session
from app.database import get_db
from app.models.catalog import Product

logger = logging.getLogger("bharatbazaar.cart")

router = APIRouter(prefix="/api/cart", tags=["cart"])

_CARTS: dict[int, list] = {}


def read_cart(db, customer_id: int) -> list[dict]:
    return _CARTS.get(customer_id, [])


@router.get("")
async def view_cart(session=Depends(current_session), db=Depends(get_db)):
    return {"items": read_cart(db, session["customer_id"])}


@router.post("/items")
async def add_to_cart(
    product_id: int,
    quantity: int = 1,
    session=Depends(current_session),
    db=Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None or not product.is_active:
        return {"added": False, "reason": "unavailable"}

    cart = _CARTS.setdefault(session["customer_id"], [])
    cart.append(
        {
            "product_id": product.id,
            "seller_id": product.seller_id,
            "title": product.title,
            "quantity": quantity,
            "unit_price": float(product.selling_price),
        }
    )
    return {"added": True, "item_count": len(cart)}


@router.delete("/items/{product_id}")
async def remove_from_cart(
    product_id: int, session=Depends(current_session), db=Depends(get_db)
):
    cart = _CARTS.get(session["customer_id"], [])
    _CARTS[session["customer_id"]] = [
        line for line in cart if line["product_id"] != product_id
    ]
    return {"removed": True}


@router.post("/abandon-ping")
async def abandoned_cart_ping(session=Depends(current_session), db=Depends(get_db)):
    """Fired by the app when the cart screen closes without a
    checkout, so the campaign job can follow up later."""
    cart = read_cart(db, session["customer_id"])
    logger.info(
        "abandoned cart customer=%s items=%s",
        session["customer_id"],
        json.dumps(cart),
    )
    return {"recorded": True}
