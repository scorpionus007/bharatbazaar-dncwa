"""Catalogue search.

A LIKE query over the title, which is enough at this catalogue size
and is the thing everybody promises to replace later.
"""

from app.models.catalog import Category, Product

PAGE_SIZE = 24


def find_products(db, category_slug: str = "", query: str = "", page: int = 1) -> dict:
    rows = db.query(Product).filter(Product.is_active.is_(True))

    if category_slug:
        category = (
            db.query(Category).filter(Category.slug == category_slug).first()
        )
        if category is not None:
            rows = rows.filter(Product.category_id == category.id)

    if query:
        rows = rows.filter(Product.title.ilike(f"%{query}%"))

    offset = max(0, (page - 1) * PAGE_SIZE)
    page_rows = rows.offset(offset).limit(PAGE_SIZE).all()

    return {
        "page": page,
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "brand": r.brand,
                "mrp": str(r.mrp),
                "selling_price": str(r.selling_price),
            }
            for r in page_rows
        ],
    }
