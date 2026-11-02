"""Totals, coupons and GST."""

from decimal import Decimal

from app.config import settings

COUPONS = {
    "FIRST100": Decimal("100"),
    "BAZAAR50": Decimal("50"),
    "DIWALI500": Decimal("500"),
}


def compute_totals(cart: list[dict], coupon_code: str = "") -> dict:
    subtotal = sum(
        Decimal(str(line["unit_price"])) * line["quantity"] for line in cart
    )
    subtotal = Decimal(subtotal)

    discount = COUPONS.get(coupon_code.upper(), Decimal("0"))
    if discount > subtotal:
        discount = subtotal

    taxable = subtotal - discount
    gst = (taxable * Decimal(str(settings.default_gst_rate)) / Decimal("100")).quantize(
        Decimal("0.01")
    )

    shipping_fee = (
        Decimal("0")
        if taxable >= settings.free_delivery_threshold
        else Decimal("49")
    )

    return {
        "subtotal": subtotal,
        "discount": discount,
        "gst": gst,
        "shipping_fee": shipping_fee,
        "total": (taxable + gst + shipping_fee).quantize(Decimal("0.01")),
    }


def seller_commission(line_total: Decimal, rate: Decimal) -> Decimal:
    return (line_total * rate / Decimal("100")).quantize(Decimal("0.01"))
