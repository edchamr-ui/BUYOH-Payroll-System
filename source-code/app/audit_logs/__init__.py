"""Audit logs blueprint."""

from flask import Blueprint


audit_logs_bp = Blueprint(
    "audit_logs",
    __name__,
    url_prefix="/audit-logs",
)


from app.audit_logs import routes
