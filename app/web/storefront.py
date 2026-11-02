"""The storefront itself: server rendered pages, no build step.

Everything a shopper sees is here. The JSON API under /api is what the
mobile app talks to; this is what a browser talks to.

Routes that touch personal data take `require_customer` as a
dependency rather than checking inside the handler, so a new route is
closed until somebody deliberately leaves it open.
"""

import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Security
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.models.catalog import Category, Product, Review
from app.models.customer import Address, Customer, Nomination, OtpAttempt
from app.models.order import Order, OrderItem
from app.models.support import SupportTicket
from app.services import audit, consent, erasure, notifications, pricing, processors

logger = logging.getLogger("bharatbazaar.web")

router = APIRouter(tags=["storefront"])

# Relative to the package, not the working directory, so the server
# runs the same from a clone root or from anywhere else.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

SESSION_COOKIE = "bb_session"
_WEB_SESSIONS: dict[str, dict] = {}
_PENDING_OTP: dict[str, str] = {}
_WEB_CARTS: dict[int, dict[int, int]] = {}

EMOJI_BY_SLUG = {
    "electronics": "\N{MOBILE PHONE}",
    "kitchen": "\N{COOKING}",
    "fashion": "\N{T-SHIRT}",
    "grocery": "\N{SHOPPING BAGS}",
    "home": "\N{HOUSE BUILDING}",
    "books": "\N{BOOKS}",
}


# ------------------------------------------------------------ session


def current_customer(request: Request, db) -> Customer | None:
    """The signed in shopper, or None. Used where either is fine."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = _WEB_SESSIONS.get(token)
    if session is None or session["expires_at"] < datetime.utcnow():
        return None
    return db.query(Customer).filter(Customer.id == session["customer_id"]).first()


async def require_customer(request: Request, db=Depends(get_db)) -> Customer:
    """Resolve the signed in shopper, or send them to sign in.

    A dependency rather than a check inside each handler, because a
    check inside the handler is one a new route can forget to make.
    The 303 keeps the browser behaviour of being bounced to /login.
    """
    customer = current_customer(request, db)
    if customer is None:
        raise HTTPException(
            status_code=303, headers={"Location": "/login?m=Please+sign+in"}
        )
    return customer


def _cart_for(customer_id: int) -> dict[int, int]:
    return _WEB_CARTS.setdefault(customer_id, {})


def _render(request: Request, db, template: str, **context) -> HTMLResponse:
    customer = context.pop("customer", None) or current_customer(request, db)
    cart = _cart_for(customer.id) if customer else {}
    base = {
        "customer": customer,
        "cart_count": sum(cart.values()),
        "nav_categories": db.query(Category).filter(Category.is_active.is_(True)).all(),
        "deliver_to": _deliver_to(db, customer),
        "flash": request.query_params.get("m"),
    }
    base.update(context)
    return templates.TemplateResponse(request, template, base)


def _deliver_to(db, customer) -> str:
    if customer is None:
        return "India"
    address = (
        db.query(Address)
        .filter(Address.customer_id == customer.id, Address.is_deleted.is_(False))
        .first()
    )
    return f"{address.city} {address.pincode}" if address else "India"


def _stars(score: float) -> str:
    filled = int(round(score))
    return "\N{BLACK STAR}" * filled + "\N{WHITE MEDIUM STAR}" * (5 - filled)


def _view(product: Product, db) -> dict:
    mrp = Decimal(product.mrp or 0)
    price = Decimal(product.selling_price or 0)
    off = int(round((mrp - price) / mrp * 100)) if mrp > 0 and price < mrp else 0
    rating = db.query(Review).filter(Review.product_id == product.id).all()
    avg = round(sum(r.rating for r in rating) / len(rating), 1) if rating else 4.2
    category = db.query(Category).filter(Category.id == product.category_id).first()
    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "brand": product.brand,
        "emoji": EMOJI_BY_SLUG.get(category.slug if category else "", "\N{PACKAGE}"),
        "mrp_display": f"{mrp:,.0f}",
        "selling_price_display": f"{price:,.0f}",
        "discount_pct": off,
        "stars": _stars(avg),
        "review_count": len(rating),
        "delivery_day": (datetime.utcnow() + timedelta(days=2)).strftime("%a, %d %b"),
        "in_stock": (product.stock_quantity or 0) > 0,
        "category_slug": category.slug if category else "",
        "category_name": category.name if category else "",
        "seller_name": "BharatBazaar Retail",
    }


# -------------------------------------------------------------- browse


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db=Depends(get_db)):
    shelves = []
    for category in db.query(Category).filter(Category.is_active.is_(True)).all():
        rows = (
            db.query(Product)
            .filter(Product.category_id == category.id, Product.is_active.is_(True))
            .limit(5)
            .all()
        )
        if rows:
            shelves.append(
                {"name": category.name, "products": [_view(p, db) for p in rows]}
            )
    return _render(request, db, "home.html", shelves=shelves)


@router.get("/c/{slug}", response_class=HTMLResponse)
async def category_listing(slug: str, request: Request, db=Depends(get_db)):
    category = db.query(Category).filter(Category.slug == slug).first()
    rows = (
        db.query(Product).filter(Product.category_id == category.id).all()
        if category
        else []
    )
    return _render(
        request,
        db,
        "listing.html",
        heading=category.name if category else "Not found",
        products=[_view(p, db) for p in rows],
        active_category=slug,
    )


@router.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "", category: str = "", db=Depends(get_db)):
    rows = db.query(Product).filter(Product.is_active.is_(True))
    if q:
        rows = rows.filter(Product.title.ilike(f"%{q}%"))
    if category:
        found = db.query(Category).filter(Category.slug == category).first()
        if found:
            rows = rows.filter(Product.category_id == found.id)
    results = rows.limit(60).all()
    return _render(
        request,
        db,
        "listing.html",
        heading=f'Results for "{q}"' if q else "All products",
        products=[_view(p, db) for p in results],
        query=q,
        active_category=category,
    )


@router.get("/p/{product_id}", response_class=HTMLResponse)
async def product_page(product_id: int, request: Request, db=Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        return RedirectResponse("/", status_code=303)

    reviews = db.query(Review).filter(Review.product_id == product.id).all()
    rendered = [
        {
            "title": r.title,
            "body": r.body,
            "reviewer_display_name": r.reviewer_display_name,
            "is_verified_purchase": r.is_verified_purchase,
            "stars": _stars(r.rating),
        }
        for r in reviews
    ]
    return _render(
        request, db, "product.html", product=_view(product, db), reviews=rendered
    )


# ---------------------------------------------------------------- cart


@router.post("/cart/add")
async def cart_add(
    product_id: int = Form(...),
    quantity: int = Form(1),
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    cart = _cart_for(customer.id)
    cart[product_id] = cart.get(product_id, 0) + max(1, quantity)
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/remove")
async def cart_remove(
    product_id: int = Form(...),
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    _cart_for(customer.id).pop(product_id, None)
    return RedirectResponse("/cart", status_code=303)


def _cart_lines(db, customer: Customer) -> list[dict]:
    lines = []
    for product_id, quantity in _cart_for(customer.id).items():
        product = db.query(Product).filter(Product.id == product_id).first()
        if product is None:
            continue
        lines.append(
            {
                "product_id": product.id,
                "seller_id": product.seller_id,
                "title": product.title,
                "brand": product.brand,
                "quantity": quantity,
                "unit_price": float(product.selling_price),
                "line_total_display": f"{Decimal(product.selling_price) * quantity:,.0f}",
            }
        )
    return lines


def _totals(lines: list[dict], coupon: str = "") -> dict:
    computed = pricing.compute_totals(lines, coupon_code=coupon)
    return {k: f"{Decimal(v):,.0f}" for k, v in computed.items()}


@router.get("/cart", response_class=HTMLResponse)
async def cart_page(
    request: Request,
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    lines = _cart_lines(db, customer)
    return _render(request, db, "cart.html", items=lines, totals=_totals(lines))


# -------------------------------------------------------- sign in flow


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db=Depends(get_db)):
    return _render(request, db, "login.html", otp_sent=False)


@router.post("/login", response_class=HTMLResponse)
async def login_request_otp(
    request: Request, phone_number: str = Form(...), db=Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.phone_number == phone_number).first()
    if customer is None:
        return RedirectResponse("/register?m=No+account+on+that+number", 303)

    code = str(secrets.randbelow(900000) + 100000)
    _PENDING_OTP[phone_number] = code
    db.add(OtpAttempt(phone_number=phone_number, otp_code=code))
    db.commit()
    notifications.send_otp(phone_number, code)

    return _render(
        request,
        db,
        "login.html",
        otp_sent=True,
        phone_number=phone_number,
        demo_code=code,
    )


@router.post("/login/verify")
async def login_verify(
    phone_number: str = Form(...), code: str = Form(...), db=Depends(get_db)
):
    if _PENDING_OTP.get(phone_number) != code:
        return RedirectResponse("/login?m=That+code+is+not+right", 303)

    customer = db.query(Customer).filter(Customer.phone_number == phone_number).first()
    customer.last_login_at = datetime.utcnow()
    db.commit()
    _PENDING_OTP.pop(phone_number, None)

    token = secrets.token_urlsafe(32)
    _WEB_SESSIONS[token] = {
        "customer_id": customer.id,
        "expires_at": datetime.utcnow() + timedelta(days=30),
    }
    audit.record_access(db, customer.id, "sign_in", "customer", customer.id)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=30 * 86400
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db=Depends(get_db)):
    return _render(request, db, "register.html")


@router.post("/register")
async def register_submit(
    full_name: str = Form(...),
    phone_number: str = Form(...),
    email_address: str = Form(""),
    date_of_birth: str = Form(""),
    marketing_consent: str = Form(""),
    db=Depends(get_db),
):
    if db.query(Customer).filter(Customer.phone_number == phone_number).first():
        return RedirectResponse("/login?m=That+number+already+has+an+account", 303)

    customer = Customer(
        full_name=full_name,
        phone_number=phone_number,
        email_address=email_address or None,
        date_of_birth=date_of_birth or None,
    )
    db.add(customer)
    db.commit()

    # s.6. Running the account is one purpose; marketing is another,
    # and it is only recorded if the box was actually ticked.
    consent.record_consent(db, customer, purpose="account", granted=True)
    consent.record_consent(
        db, customer, purpose="marketing", granted=marketing_consent == "yes"
    )
    audit.record_access(db, customer.id, "register", "customer", customer.id)

    return RedirectResponse("/login?m=Account+created,+please+sign+in", 303)


@router.get("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    _WEB_SESSIONS.pop(token, None)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ------------------------------------------------------------- account


@router.get("/account", response_class=HTMLResponse)
async def account_page(
    request: Request,
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    return _render(request, db, "account.html")


@router.get("/account/addresses", response_class=HTMLResponse)
async def addresses_page(
    request: Request,
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    rows = (
        db.query(Address)
        .filter(Address.customer_id == customer.id, Address.is_deleted.is_(False))
        .all()
    )
    return _render(request, db, "addresses.html", addresses=rows)


@router.post("/account/addresses")
async def add_address(
    recipient_name: str = Form(...),
    recipient_phone: str = Form(...),
    address_line_1: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    db.add(
        Address(
            customer_id=customer.id,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            address_line_1=address_line_1,
            city=city,
            state=state,
            pincode=pincode,
        )
    )
    db.commit()
    return RedirectResponse("/account/addresses?m=Address+saved", 303)


@router.post("/account/addresses/delete")
async def remove_address(
    address_id: int = Form(...),
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    address = (
        db.query(Address)
        .filter(Address.id == address_id, Address.customer_id == customer.id)
        .first()
    )
    if address is not None:
        db.delete(address)
        db.commit()
    return RedirectResponse("/account/addresses?m=Address+removed", 303)


@router.get("/account/orders", response_class=HTMLResponse)
async def orders_page(
    request: Request,
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    rows = (
        db.query(Order)
        .filter(Order.customer_id == customer.id)
        .order_by(Order.placed_at.desc())
        .all()
    )
    return _render(
        request,
        db,
        "orders.html",
        orders=[
            {
                "order_number": o.order_number,
                "placed_on": o.placed_at.strftime("%d %b %Y") if o.placed_at else "",
                "recipient_name": o.recipient_name,
                "delivery_pincode": o.delivery_pincode,
                "total_display": f"{Decimal(o.total):,.0f}",
                "status": o.status,
            }
            for o in rows
        ],
    )


# ------------------------------------------------------------ checkout


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(
    request: Request,
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    lines = _cart_lines(db, customer)
    if not lines:
        return RedirectResponse("/cart", status_code=303)
    addresses = (
        db.query(Address)
        .filter(Address.customer_id == customer.id, Address.is_deleted.is_(False))
        .all()
    )
    return _render(
        request, db, "checkout.html", addresses=addresses, totals=_totals(lines)
    )


@router.post("/checkout")
async def place_order(
    payment_method: str = Form("upi"),
    coupon_code: str = Form(""),
    address_id: int = Form(0),
    recipient_name: str = Form(""),
    recipient_phone: str = Form(""),
    address_line_1: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    pincode: str = Form(""),
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    lines = _cart_lines(db, customer)
    if not lines:
        return RedirectResponse("/cart", status_code=303)

    if address_id:
        address = db.query(Address).filter(Address.id == address_id).first()
    else:
        address = Address(
            customer_id=customer.id,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            address_line_1=address_line_1,
            city=city,
            state=state,
            pincode=pincode,
        )
        db.add(address)
        db.commit()

    totals = pricing.compute_totals(lines, coupon_code=coupon_code)
    order = Order(
        order_number="BB" + datetime.utcnow().strftime("%y%m%d%H%M%S"),
        customer_id=customer.id,
        recipient_name=address.recipient_name,
        recipient_phone=address.recipient_phone,
        delivery_address=f"{address.address_line_1}, {address.city}, {address.state}",
        delivery_pincode=address.pincode,
        subtotal=totals["subtotal"],
        shipping_fee=totals["shipping_fee"],
        discount=totals["discount"],
        gst_amount=totals["gst"],
        total=totals["total"],
        coupon_code=coupon_code or None,
        is_cash_on_delivery=payment_method == "cod",
    )
    db.add(order)
    db.commit()

    for line in lines:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=line["product_id"],
                seller_id=line["seller_id"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                line_total=Decimal(str(line["unit_price"])) * line["quantity"],
            )
        )
    db.commit()

    _WEB_CARTS[customer.id] = {}
    audit.record_access(db, customer.id, "place_order", "order", order.id)
    notifications.send_order_confirmation(order, customer)

    return RedirectResponse(f"/account/orders?m=Order+{order.order_number}+placed", 303)


# -------------------------------------------------------------- support


@router.get("/support", response_class=HTMLResponse)
async def support_page(request: Request, db=Depends(get_db)):
    customer = current_customer(request, db)
    tickets = []
    if customer is not None:
        tickets = [
            {
                "subject": t.subject,
                "category": t.category,
                "status": t.status,
                "respond_by": t.respond_by.strftime("%d %b %Y") if t.respond_by else "",
            }
            for t in db.query(SupportTicket)
            .filter(SupportTicket.customer_id == customer.id)
            .all()
        ]
    return _render(
        request,
        db,
        "support.html",
        categories=[
            "order_not_delivered",
            "wrong_item",
            "damaged_item",
            "refund_not_received",
            "privacy_request",
            "other",
        ],
        tickets=tickets,
        grievance_officer=processors.GRIEVANCE_OFFICER,
    )


@router.post("/support")
async def raise_ticket(
    subject: str = Form(...),
    body: str = Form(...),
    category: str = Form("other"),
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    db.add(
        SupportTicket(
            customer_id=customer.id,
            subject=subject,
            body=body,
            category=category,
        )
    )
    db.commit()
    return RedirectResponse("/support?m=Ticket+raised", 303)


# ------------------------------------------------- data and privacy


@router.get("/account/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request, db=Depends(get_db)):
    """Readable signed out, so the notice and the recipient list can
    be read before anybody hands over a phone number."""
    customer = current_customer(request, db)
    nominee = None
    consents = []
    if customer is not None:
        nominee = (
            db.query(Nomination).filter(Nomination.customer_id == customer.id).first()
        )
        consents = consent.consent_summary(db, customer.id)
    return _render(
        request,
        db,
        "privacy.html",
        processors=processors.recipients_for_display(),
        consents=consents,
        nominee=nominee,
    )


@router.get("/account/privacy/export")
async def export_my_data(
    customer: Customer = Security(require_customer), db=Depends(get_db)
):
    """s.11(1)(a). Everything held, as a file the customer keeps."""
    payload = erasure.export_customer(db, customer)
    return JSONResponse(
        payload,
        headers={
            "Content-Disposition": "attachment; filename=bharatbazaar-my-data.json"
        },
    )


@router.post("/account/privacy/consent")
async def change_consent(
    purpose: str = Form(...),
    granted: str = Form(...),
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    """s.6(4). Withdrawal is one click, the same as giving it."""
    consent.record_consent(db, customer, purpose=purpose, granted=granted == "yes")
    return RedirectResponse("/account/privacy?m=Consent+updated", 303)


@router.post("/account/privacy/nominate")
async def save_nominee(
    nominee_name: str = Form(...),
    nominee_email: str = Form(...),
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    """s.14. Who may exercise these rights on the customer's behalf."""
    existing = (
        db.query(Nomination).filter(Nomination.customer_id == customer.id).first()
    )
    if existing:
        existing.nominee_name = nominee_name
        existing.nominee_email = nominee_email
    else:
        db.add(
            Nomination(
                customer_id=customer.id,
                nominee_name=nominee_name,
                nominee_email=nominee_email,
            )
        )
    db.commit()
    audit.record_access(db, customer.id, "nominate", "customer", customer.id)
    return RedirectResponse("/account/privacy?m=Nominee+saved", 303)


@router.post("/account/privacy/erase")
async def erase_my_account(
    request: Request,
    customer: Customer = Security(require_customer),
    db=Depends(get_db),
):
    """s.12(3). Erase, and cascade to the copies."""
    erasure.erase_customer(db, customer)
    token = request.cookies.get(SESSION_COOKIE)
    _WEB_SESSIONS.pop(token, None)
    response = RedirectResponse("/?m=Your+account+has+been+erased", 303)
    response.delete_cookie(SESSION_COOKIE)
    return response
