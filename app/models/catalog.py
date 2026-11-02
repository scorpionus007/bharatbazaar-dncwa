"""Catalogue: products, categories, reviews and the wishlist."""

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


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    hsn_code = Column(String(8))
    gst_rate = Column(Numeric(4, 2), default=18.00)
    is_active = Column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    brand = Column(String(120))
    sku = Column(String(64), index=True)

    mrp = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reviews = relationship("Review", back_populates="product")


class Review(Base):
    """A product review.

    Displayed publicly with the reviewer's full name, which is the
    name on their account rather than a handle they chose.
    """

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    # Nullable so an erased customer's review can stay up without
    # still pointing at them. See app/services/erasure.py.
    customer_id = Column(Integer, ForeignKey("customers.id"))

    rating = Column(Integer, nullable=False)
    title = Column(String(255))
    body = Column(Text)
    reviewer_display_name = Column(String(255))
    is_verified_purchase = Column(Boolean, default=False)
    photo_urls = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    # Five years. After that the product has usually gone and the
    # review is a person's writing with their name beside it.
    expires_at = Column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=365 * 5)
    )

    product = relationship("Product", back_populates="reviews")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)


class BrowsingEvent(Base):
    """Every product view, for the recommendation model.

    Joined to the customer id rather than to an anonymous session, so
    it is a per person browsing history with no end date on it.
    """

    __tablename__ = "browsing_events"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"))

    session_id = Column(String(64))
    device_id = Column(String(64))
    ip_address = Column(String(45))
    referrer = Column(String(512))
    dwell_seconds = Column(Integer)

    viewed_at = Column(DateTime, default=datetime.utcnow, index=True)
    # Six months. A recommendation model does not improve on a view
    # from two years ago and the row is still a person's history.
    expires_at = Column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=180), index=True
    )
