"""The job that makes a retention period real, s.8(7).

A period nothing enforces is a policy, not a safeguard. This runs
nightly, deletes what has passed its date, and logs counts rather
than rows: a cleanup job that logs what it deleted reintroduces the
data it just removed, into a log that is copied more widely than the
table was.
"""

import logging
from datetime import datetime

from app.models.catalog import BrowsingEvent
from app.models.customer import (
    AuditLog,
    Customer,
    Nomination,
    OtpAttempt,
    RETENTION_DAYS,
)
from app.models.support import SupportTicket

logger = logging.getLogger("bharatbazaar.retention")

EXPIRING_MODELS = (
    Customer,
    OtpAttempt,
    Nomination,
    AuditLog,
    BrowsingEvent,
    SupportTicket,
)


def delete_expired(db) -> dict:
    """Erase every row past its date. Returns counts, never values."""
    now = datetime.utcnow()
    deleted = {}
    for model in EXPIRING_MODELS:
        rows = db.query(model).filter(model.expires_at <= now).all()
        for row in rows:
            db.delete(row)
        deleted[model.__tablename__] = len(rows)
    db.commit()

    logger.info("retention sweep deleted %s", deleted)
    return deleted


def scheduled_cleanup_job(db) -> dict:
    """Entry point for the nightly scheduler."""
    result = delete_expired(db)
    _record_heartbeat(datetime.utcnow())
    return result


def _record_heartbeat(now: datetime) -> None:
    """So that a job which stops running is noticed.

    The failure worth guarding is not the job erroring, which is
    visible, but the job quietly not being scheduled at all.
    """
    logger.info("retention heartbeat at %s, periods=%s", now.isoformat(), RETENTION_DAYS)
