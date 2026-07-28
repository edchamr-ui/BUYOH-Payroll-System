"""Reusable audit logging service."""

from app.extensions import db
from app.models import AuditLog


class AuditLogService:
    """Create audit records for important system activity."""

    @staticmethod
    def log(
        *,
        action: str,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        commit: bool = True,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Set commit=False when the audit entry must be committed
        together with another business operation.
        """

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=ip_address,
        )

        db.session.add(audit_log)

        if commit:
            db.session.commit()

        return audit_log
