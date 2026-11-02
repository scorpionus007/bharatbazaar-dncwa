"""Table definitions, imported here so metadata is complete."""

from app.models.catalog import (
    BrowsingEvent,
    Category,
    Product,
    Review,
    WishlistItem,
)
from app.models.customer import (
    Address,
    Customer,
    OtpAttempt,
    SavedPaymentMethod,
)
from app.models.order import (
    DeliveryTracking,
    Order,
    OrderItem,
    Payment,
)
from app.models.seller import Seller, SellerDocument, SellerPayout
from app.models.support import AbuseReport, ReturnRequest, SupportTicket

__all__ = [
    "AbuseReport",
    "Address",
    "BrowsingEvent",
    "Category",
    "Customer",
    "DeliveryTracking",
    "Order",
    "OrderItem",
    "OtpAttempt",
    "Payment",
    "Product",
    "ReturnRequest",
    "Review",
    "SavedPaymentMethod",
    "Seller",
    "SellerDocument",
    "SellerPayout",
    "SupportTicket",
    "WishlistItem",
]
