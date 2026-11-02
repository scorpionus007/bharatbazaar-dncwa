"""The s.8(1) record.

Section 8(1) puts the burden of demonstrating compliance on the Data
Fiduciary, and an access request nobody can prove was served is the
same as one that was not.
"""

import logging
from datetime import datetime

from app.models.customer import AuditLog

logger = logging.getLogger("bharatbazaar.audit")


def record_access(db, actor_customer_id, action: str, resource_type: str,
                  resource_id) -> None:
    """Who touched what. Identifiers only, never values."""
    db.add(
        AuditLog(
            actor_customer_id=actor_customer_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
        )
    )
    db.commit()


def history_for(db, customer_id: int, limit: int = 100) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .filter(AuditLog.actor_customer_id == customer_id)
        .order_by(AuditLog.occurred_at.desc())
        .limit(limit)
        .all()
    )


def generate_compliance_report(db, since=None, until=None) -> dict:
    """s.8(1). The trail, as a report somebody outside can be handed.

    Section 8(1) makes the Data Fiduciary responsible for
    demonstrating compliance, and a table only a DBA can read is not
    a demonstration. This is what gets attached to an answer to the
    Board or to a customer who asks what was done with their request.
    """
    rows = db.query(AuditLog)
    if since is not None:
        rows = rows.filter(AuditLog.occurred_at >= since)
    if until is not None:
        rows = rows.filter(AuditLog.occurred_at <= until)
    rows = rows.order_by(AuditLog.occurred_at).all()

    by_action: dict[str, int] = {}
    for row in rows:
        by_action[row.action] = by_action.get(row.action, 0) + 1

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period": {
            "from": since.isoformat() if since else None,
            "to": until.isoformat() if until else None,
        },
        "total_events": len(rows),
        "by_action": by_action,
        "events": [
            {
                "occurred_at": row.occurred_at.isoformat(),
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "actor_customer_id": row.actor_customer_id,
            }
            for row in rows
        ],
    }


def rights_requests_report(db) -> dict:
    """What was asked for under Chapter III, and whether it was served.

    The report a Data Protection Officer is asked for first, and the
    one almost nothing can produce because the requests were served
    by hand and never recorded as a class.
    """
    rights = ("export", "erase", "nominate", "consent_withdrawn", "correction")
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.action.in_(rights))
        .order_by(AuditLog.occurred_at.desc())
        .all()
    )
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "served": len(rows),
        "by_right": {r: sum(1 for x in rows if x.action == r) for r in rights},
    }
