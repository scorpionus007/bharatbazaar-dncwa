"""Seller onboarding and KYC.

A marketplace seller is a person too, and the KYC pack is the most
sensitive data in the whole system: Aadhaar, PAN, bank account and a
cancelled cheque image. It is collected once at onboarding and then
sits in the table for the life of the account.
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
from sqlalchemy.orm import relationship

from app.database import Base


class Seller(Base):
    """A marketplace seller."""

    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True)

    legal_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    contact_phone = Column(String(15), nullable=False)
    contact_email = Column(String(320), nullable=False)

    gst_number = Column(String(15), index=True)
    pan_number = Column(String(10))
    aadhaar_number = Column(String(12))

    registered_address = Column(Text)
    pickup_pincode = Column(String(6))

    bank_account_number = Column(String(20))
    bank_ifsc = Column(String(11))
    account_holder_name = Column(String(255))

    commission_rate = Column(Numeric(5, 2), default=15.00)
    is_active = Column(Boolean, default=True)
    onboarded_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("SellerDocument", back_populates="seller")


class SellerDocument(Base):
    """Scans of whatever the seller uploaded at onboarding.

    The object key is stored here and the file itself goes to object
    storage. Nothing ever deletes either one.
    """

    __tablename__ = "seller_documents"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)

    document_type = Column(String(32), nullable=False)
    storage_key = Column(String(512), nullable=False)
    original_filename = Column(String(255))
    verified = Column(Boolean, default=False)
    verified_by = Column(String(120))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("Seller", back_populates="documents")


class SellerPayout(Base):
    """Weekly settlement to the seller's bank account."""

    __tablename__ = "seller_payouts"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)

    amount = Column(Numeric(12, 2), nullable=False)
    bank_account_number = Column(String(20), nullable=False)
    bank_ifsc = Column(String(11), nullable=False)
    utr_reference = Column(String(32))
    status = Column(String(16), default="pending")
    settled_at = Column(DateTime)
