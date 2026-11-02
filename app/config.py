"""Runtime configuration.

Everything is read from the environment with a development default,
which is how it has always been. The storage region is here because
the seller document bucket needed one.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings:
    app_name = "BharatBazaar"
    environment = os.environ.get("ENVIRONMENT", "development")

    # SQLite by default so the storefront runs from a clone with no
    # database to stand up first. The path is absolute, so the server
    # finds the same file wherever it was started from. Production
    # passes a Postgres URL.
    database_url = os.environ.get(
        "DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'bharatbazaar.db'}"
    )
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Seller KYC documents and product images.
    object_storage_bucket = os.environ.get("S3_BUCKET", "bharatbazaar-media")
    object_storage_region = os.environ.get("S3_REGION", "ap-south-1")

    payment_gateway = "razorpay"
    razorpay_key_id = os.environ.get("RAZORPAY_KEY_ID", "")
    razorpay_key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")

    sms_provider = "msg91"
    msg91_auth_key = os.environ.get("MSG91_AUTH_KEY", "")

    otp_length = 6
    otp_validity_seconds = 300
    session_validity_days = 90

    free_delivery_threshold = 499
    default_gst_rate = 18.0


settings = Settings()
