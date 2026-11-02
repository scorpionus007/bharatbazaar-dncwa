"""Customer, address and wallet tables.

BharatBazaar signs people up on a phone number, because that is what
works in India: a large share of customers have no email address and
the OTP is the whole login flow. Everything else hangs off that.
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


class Customer(Base):
    """A shopper.

    The date of birth is here because the age gate on alcohol and the
    birthday coupon campaign both wanted it, and nobody took it out
    when the alcohol category was dropped.
    """

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)

    phone_number = Column(String(15), nullable=False, unique=True, index=True)
    email_address = Column(String(320), index=True)
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(String(10))
    gender = Column(String(16))

    password_hash = Column(Text)
    otp_secret = Column(String(64))

    # One flag for everything. Nobody can say which notice this was
    # taken against or when, and switching it off leaves no record
    # that it was ever on.
    marketing_opt_in = Column(Boolean, default=True, nullable=False)

    referral_code = Column(String(16), index=True)
    referred_by = Column(Integer, ForeignKey("customers.id"))

    loyalty_points = Column(Integer, default=0)
    wallet_balance = Column(Numeric(10, 2), default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)

    addresses = relationship("Address", back_populates="customer")
    orders = relationship("Order", back_populates="customer")


class Address(Base):
    """A delivery address.

    Kept forever, including for addresses the customer deleted from
    the app, because the order history joins against it and somebody
    decided a soft delete was safer than a hard one.
    """

    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    label = Column(String(32))
    recipient_name = Column(String(255), nullable=False)
    recipient_phone = Column(String(15), nullable=False)

    address_line_1 = Column(String(255), nullable=False)
    address_line_2 = Column(String(255))
    landmark = Column(String(255))
    city = Column(String(120), nullable=False)
    state = Column(String(120), nullable=False)
    pincode = Column(String(6), nullable=False, index=True)

    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))

    is_default = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="addresses")


class SavedPaymentMethod(Base):
    """A saved card or UPI handle."""

    __tablename__ = "saved_payment_methods"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    method_type = Column(String(16), nullable=False)
    upi_id = Column(String(120))
    card_last_four = Column(String(4))
    card_network = Column(String(32))
    card_holder_name = Column(String(255))
    gateway_token = Column(String(255))

    created_at = Column(DateTime, default=datetime.utcnow)


class OtpAttempt(Base):
    """Every OTP sent, kept for the fraud team.

    No expiry on the row, so the fraud team has a complete history of
    which number logged in from which device going back to launch.
    """

    __tablename__ = "otp_attempts"

    id = Column(Integer, primary_key=True)
    phone_number = Column(String(15), nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    device_id = Column(String(64))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    succeeded = Column(Boolean, default=False)
    attempted_at = Column(DateTime, default=datetime.utcnow)
