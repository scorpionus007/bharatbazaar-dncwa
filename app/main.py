"""BharatBazaar API.

A marketplace: customers, sellers, a catalogue, checkout, payments,
delivery tracking and support. Everything is mounted here.
"""

from fastapi import FastAPI

from app.api import admin, auth, cart, catalog, customers, orders, payments, sellers, support
from app.config import settings
from app.utils.logging import configure

logger = configure()

app = FastAPI(
    title=settings.app_name,
    description="Marketplace API",
    version="4.2.0",
)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(catalog.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(sellers.router)
app.include_router(support.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}


@app.on_event("startup")
async def on_startup():
    logger.info(
        "%s starting in %s, storage in %s",
        settings.app_name,
        settings.environment,
        settings.object_storage_region,
    )
