"""Customer, address and wallet tables.

BharatBazaar signs people up on a phone number, because that is what
works in India: a large share of customers have no email address and
the OTP is the whole login flow. Everything else hangs off that.
"""

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

# s.8(7): the point at which a purpose is no longer served and the row
# has to go. Per category, because a grievance record and an OTP
# attempt do not deserve the same life.
RETENTION_DAYS = {
    "account": 365 * 3,
    "order": 365 * 8,
    "grievance": 365 * 2,
    "otp": 90,
    "browsing": 180,
}


def expires_in(category: str) -> datetime:
    return datetime.utcnow() + timedelta(days=RETENTION_DAYS[category])


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

    # Kept only so the old mobile build keeps deserialising. The
    # answer that counts is the newest ConsentEvent row for the
    # purpose; see app/services/consent.py.
    marketing_opt_in = Column(Boolean, default=False, nullable=False)

    referral_code = Column(String(16), index=True)
    referred_by = Column(Integer, ForeignKey("customers.id"))

    loyalty_points = Column(Integer, default=0)
    wallet_balance = Column(Numeric(10, 2), default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)
    # s.8(7)(a). The row carries the date it stops being needed.
    expires_at = Column(DateTime, default=lambda: expires_in("account"), index=True)

    addresses = relationship("Address", back_populates="customer")
    orders = relationship("Order", back_populates="customer")
    consents = relationship("ConsentEvent", back_populates="customer")


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
    expires_at = Column(DateTime, default=lambda: expires_in("account"), index=True)

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
    expires_at = Column(DateTime, default=lambda: expires_in("account"), index=True)


class OtpAttempt(Base):
    """Every OTP sent, kept for the fraud team.

    Ninety days, which is as far back as a chargeback can reach. The
    sweep in app/services/retention.py deletes the rest.
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
    expires_at = Column(DateTime, default=lambda: expires_in("otp"), index=True)


class ConsentEvent(Base):
    """s.6. An event, not a flag.

    A boolean records that somebody agreed. It does not record what
    they agreed to, when, or which notice they were shown, and none of
    those can be reconstructed afterwards. A withdrawal is a second
    row rather than a mutation, so the history survives it.
    """

    __tablename__ = "consent_events"

    id = Column(Integer, primary_key=True)
    customer_id = Column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )

    purpose = Column(String(64), nullable=False)
    granted = Column(Boolean, nullable=False)
    notice_version = Column(String(32), nullable=False)
    source = Column(String(32), default="web")
    consented_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="consents")


class Nomination(Base):
    """s.14. Who may exercise these rights if the Data Principal cannot.

    Almost nothing implements this, which is why it is here.
    """

    __tablename__ = "nominations"

    id = Column(Integer, primary_key=True)
    customer_id = Column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), unique=True
    )
    nominee_name = Column(String(255), nullable=False)
    nominee_email = Column(String(320), nullable=False)
    nominated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: expires_in("account"))


class AuditLog(Base):
    """s.8(1). Who read or changed personal data, and when.

    Written from the service layer rather than from each handler, so a
    new endpoint cannot forget to record itself.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_customer_id = Column(Integer, index=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=False)
    occurred_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, default=lambda: expires_in("order"))
