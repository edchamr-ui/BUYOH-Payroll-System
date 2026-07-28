"""Audit log routes."""

from flask import (
    render_template,
    request,
)
from flask_login import login_required
from sqlalchemy import or_

from app.audit_logs import audit_logs_bp
from app.models import AuditLog, User


@audit_logs_bp.route("/")
@login_required
def index():
    """Display system audit logs with optional filtering."""

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    action_filter = request.args.get(
        "action",
        "",
    ).strip()

    query = AuditLog.query

    if search_term:
        search_pattern = f"%{search_term}%"

        query = (
            query
            .outerjoin(
                User,
                AuditLog.user_id == User.id,
            )
            .filter(
                or_(
                    AuditLog.action.ilike(
                        search_pattern
                    ),
                    AuditLog.entity_type.ilike(
                        search_pattern
                    ),
                    AuditLog.description.ilike(
                        search_pattern
                    ),
                    AuditLog.ip_address.ilike(
                        search_pattern
                    ),
                    User.username.ilike(
                        search_pattern
                    ),
                    User.first_name.ilike(
                        search_pattern
                    ),
                    User.last_name.ilike(
                        search_pattern
                    ),
                )
            )
        )

    if action_filter:
        query = query.filter(
            AuditLog.action == action_filter
        )

    logs = (
        query
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .limit(500)
        .all()
    )

    available_actions = [
        action
        for action, in (
            AuditLog.query
            .with_entities(AuditLog.action)
            .distinct()
            .order_by(AuditLog.action.asc())
            .all()
        )
    ]

    return render_template(
        "audit_logs/index.html",
        logs=logs,
        search_term=search_term,
        action_filter=action_filter,
        available_actions=available_actions,
    )
