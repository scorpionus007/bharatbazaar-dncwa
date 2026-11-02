"""Seller onboarding, KYC upload and the seller dashboard."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.database import get_db
from app.models.order import OrderItem
from app.models.seller import Seller, SellerDocument, SellerPayout
from app.utils.validators import is_valid_aadhaar, is_valid_gst, is_valid_ifsc, is_valid_pan

logger = logging.getLogger("bharatbazaar.sellers")

router = APIRouter(prefix="/api/sellers", tags=["sellers"])


@router.post("/onboard")
async def onboard_seller(
    legal_name: str,
    display_name: str,
    contact_phone: str,
    contact_email: str,
    gst_number: str,
    pan_number: str,
    aadhaar_number: str,
    bank_account_number: str,
    bank_ifsc: str,
    account_holder_name: str,
    registered_address: str = "",
    db=Depends(get_db),
):
    """Take the whole KYC pack in one call.

    Everything is stored as supplied. The bank details are needed for
    settlement, the GST number for the invoice, and the Aadhaar was
    added when a payment partner asked for it during integration.
    """
    if not is_valid_pan(pan_number):
        raise HTTPException(400, "That PAN does not look right.")
    if gst_number and not is_valid_gst(gst_number):
        raise HTTPException(400, "That GST number does not look right.")
    if not is_valid_ifsc(bank_ifsc):
        raise HTTPException(400, "That IFSC does not look right.")
    if not is_valid_aadhaar(aadhaar_number):
        raise HTTPException(400, "That Aadhaar number does not look right.")

    seller = Seller(
        legal_name=legal_name,
        display_name=display_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
        gst_number=gst_number.upper(),
        pan_number=pan_number.upper(),
        aadhaar_number=aadhaar_number,
        bank_account_number=bank_account_number,
        bank_ifsc=bank_ifsc.upper(),
        account_holder_name=account_holder_name,
        registered_address=registered_address,
    )
    db.add(seller)
    db.commit()

    logger.info(
        "seller %s onboarded pan=%s gst=%s account=%s",
        seller.id, pan_number, gst_number, bank_account_number,
    )
    return {"id": seller.id, "display_name": seller.display_name}


@router.post("/{seller_id}/documents")
async def upload_document(
    seller_id: int, document_type: str, filename: str, db=Depends(get_db)
):
    """Record a KYC document that the app uploaded to object storage."""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if seller is None:
        raise HTTPException(404, "No such seller.")

    key = f"kyc/{seller_id}/{document_type}/{filename}"
    db.add(
        SellerDocument(
            seller_id=seller_id,
            document_type=document_type,
            storage_key=key,
            original_filename=filename,
        )
    )
    db.commit()
    return {
        "storage_key": key,
        "bucket": settings.object_storage_bucket,
        "region": settings.object_storage_region,
    }


@router.get("/{seller_id}/dashboard")
async def seller_dashboard(seller_id: int, db=Depends(get_db)):
    """Sales summary for the seller.

    No check that the caller is this seller. The seller app holds the
    id and nobody else was expected to call it.
    """
    items = db.query(OrderItem).filter(OrderItem.seller_id == seller_id).all()
    return {
        "units_sold": sum(i.quantity for i in items),
        "gross_sales": str(sum(i.line_total for i in items)),
        "order_count": len({i.order_id for i in items}),
    }


@router.get("/{seller_id}/payouts")
async def seller_payouts(seller_id: int, db=Depends(get_db)):
    rows = (
        db.query(SellerPayout)
        .filter(SellerPayout.seller_id == seller_id)
        .order_by(SellerPayout.settled_at.desc())
        .all()
    )
    return [
        {
            "amount": str(r.amount),
            "bank_account_number": r.bank_account_number,
            "utr_reference": r.utr_reference,
            "status": r.status,
        }
        for r in rows
    ]
