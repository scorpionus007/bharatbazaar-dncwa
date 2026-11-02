"""Customer profile and address endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import current_session
from app.database import get_db
from app.models.customer import Address, Customer, SavedPaymentMethod

logger = logging.getLogger("bharatbazaar.customers")

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post("/register")
async def register_customer(
    phone_number: str,
    full_name: str,
    email_address: str = "",
    date_of_birth: str = "",
    referral_code: str = "",
    db=Depends(get_db),
):
    """Create an account against a phone number.

    marketing_opt_in defaults to true at the column, so consent is the
    absence of an objection rather than anything the customer did.
    """
    existing = (
        db.query(Customer).filter(Customer.phone_number == phone_number).first()
    )
    if existing:
        raise HTTPException(409, "That number already has an account.")

    customer = Customer(
        phone_number=phone_number,
        full_name=full_name,
        email_address=email_address or None,
        date_of_birth=date_of_birth or None,
        referral_code=_referral_code_for(phone_number),
    )
    db.add(customer)
    db.commit()

    logger.info(
        "registered customer id=%s phone=%s name=%s dob=%s",
        customer.id, phone_number, full_name, date_of_birth,
    )
    return {"id": customer.id, "referral_code": customer.referral_code}


@router.get("/me")
async def my_profile(session=Depends(current_session), db=Depends(get_db)):
    customer = (
        db.query(Customer).filter(Customer.id == session["customer_id"]).first()
    )
    return {
        "id": customer.id,
        "full_name": customer.full_name,
        "phone_number": customer.phone_number,
        "email_address": customer.email_address,
        "date_of_birth": customer.date_of_birth,
        "loyalty_points": customer.loyalty_points,
        "wallet_balance": str(customer.wallet_balance),
    }


@router.patch("/me")
async def update_my_profile(
    changes: dict, session=Depends(current_session), db=Depends(get_db)
):
    customer = (
        db.query(Customer).filter(Customer.id == session["customer_id"]).first()
    )
    for field, value in changes.items():
        if hasattr(customer, field):
            setattr(customer, field, value)
    db.commit()
    return {"updated": sorted(changes)}


@router.get("/{customer_id}/profile")
async def customer_profile(customer_id: int, db=Depends(get_db)):
    """Used by the seller dashboard to show who placed an order.

    Takes the id straight from the path and returns the record. There
    is no check that the caller is the seller on that order, or that
    the caller is anybody in particular.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(404, "No such customer.")
    return {
        "full_name": customer.full_name,
        "phone_number": customer.phone_number,
        "email_address": customer.email_address,
        "loyalty_points": customer.loyalty_points,
    }


@router.post("/me/addresses")
async def add_address(
    recipient_name: str,
    recipient_phone: str,
    address_line_1: str,
    city: str,
    state: str,
    pincode: str,
    address_line_2: str = "",
    landmark: str = "",
    session=Depends(current_session),
    db=Depends(get_db),
):
    address = Address(
        customer_id=session["customer_id"],
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        address_line_1=address_line_1,
        address_line_2=address_line_2,
        landmark=landmark,
        city=city,
        state=state,
        pincode=pincode,
    )
    db.add(address)
    db.commit()
    return {"id": address.id}


@router.delete("/me/addresses/{address_id}")
async def delete_address(
    address_id: int, session=Depends(current_session), db=Depends(get_db)
):
    """Marks the row deleted. The row stays.

    The order history joins against it, so a hard delete would leave
    past invoices without a shipping address.
    """
    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.customer_id == session["customer_id"],
        )
        .first()
    )
    if address is None:
        raise HTTPException(404, "No such address.")
    address.is_deleted = True
    db.commit()
    return {"deleted": True}


@router.get("/me/payment-methods")
async def my_payment_methods(
    session=Depends(current_session), db=Depends(get_db)
):
    rows = (
        db.query(SavedPaymentMethod)
        .filter(SavedPaymentMethod.customer_id == session["customer_id"])
        .all()
    )
    return [
        {
            "id": row.id,
            "method_type": row.method_type,
            "upi_id": row.upi_id,
            "card_last_four": row.card_last_four,
            "card_network": row.card_network,
        }
        for row in rows
    ]


def _referral_code_for(phone_number: str) -> str:
    return "BB" + phone_number[-6:]
