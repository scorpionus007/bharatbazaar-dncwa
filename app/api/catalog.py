"""Catalogue browsing, search and reviews."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.auth import current_session
from app.database import get_db
from app.models.catalog import BrowsingEvent, Category, Product, Review
from app.services import search

logger = logging.getLogger("bharatbazaar.catalog")

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/categories")
async def list_categories(db=Depends(get_db)):
    rows = db.query(Category).filter(Category.is_active.is_(True)).all()
    return [{"id": r.id, "name": r.name, "slug": r.slug} for r in rows]


@router.get("/products")
async def list_products(
    category_slug: str = "", query: str = "", page: int = 1, db=Depends(get_db)
):
    return search.find_products(
        db, category_slug=category_slug, query=query, page=page
    )


@router.get("/products/{product_id}")
async def product_detail(
    product_id: int,
    request: Request,
    x_device_id: str = Header(default=""),
    db=Depends(get_db),
):
    """Product page, and the view event that feeds recommendations."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(404, "No such product.")

    db.add(
        BrowsingEvent(
            customer_id=_customer_id_from(request),
            product_id=product.id,
            session_id=request.headers.get("x-session-id"),
            device_id=x_device_id,
            ip_address=request.client.host if request.client else None,
            referrer=request.headers.get("referer"),
        )
    )
    db.commit()

    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "brand": product.brand,
        "mrp": str(product.mrp),
        "selling_price": str(product.selling_price),
        "in_stock": product.stock_quantity > 0,
    }


@router.get("/products/{product_id}/reviews")
async def product_reviews(product_id: int, db=Depends(get_db)):
    rows = db.query(Review).filter(Review.product_id == product_id).all()
    return [
        {
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "reviewer": r.reviewer_display_name,
            "verified_purchase": r.is_verified_purchase,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/products/{product_id}/reviews")
async def write_review(
    product_id: int,
    rating: int,
    title: str = "",
    body: str = "",
    session=Depends(current_session),
    db=Depends(get_db),
):
    from app.models.customer import Customer

    customer = (
        db.query(Customer).filter(Customer.id == session["customer_id"]).first()
    )
    review = Review(
        product_id=product_id,
        customer_id=customer.id,
        rating=rating,
        title=title,
        body=body,
        # The account name, published next to the review. Nobody is
        # asked whether they want their real name on it.
        reviewer_display_name=customer.full_name,
    )
    db.add(review)
    db.commit()
    return {"id": review.id}


def _customer_id_from(request: Request):
    from app.api.auth import _SESSIONS

    token = request.headers.get("authorization", "").partition(" ")[2]
    session = _SESSIONS.get(token)
    return session["customer_id"] if session else None
