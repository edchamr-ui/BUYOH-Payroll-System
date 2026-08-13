"""Unauthenticated operational health endpoints."""

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


health_bp = Blueprint("health", __name__)


def database_is_ready():
    """Return whether a fresh connection can execute a minimal query."""

    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        current_app.logger.warning(
            "Database readiness check failed.",
            exc_info=True,
        )
        return False
    return True


def health_response(payload, status_code):
    """Return a JSON health response that must never be cached."""

    response = jsonify(payload)
    response.status_code = status_code
    response.headers["Cache-Control"] = "no-store"
    return response


@health_bp.get("/health/live")
def live():
    """Confirm that the application process can serve requests."""

    return health_response({"status": "ok"}, 200)


@health_bp.get("/health/ready")
def ready():
    """Confirm that the application can reach its database dependency."""

    if database_is_ready():
        return health_response(
            {
                "status": "ok",
                "checks": {"database": "ok"},
            },
            200,
        )

    return health_response(
        {
            "status": "unavailable",
            "checks": {"database": "unavailable"},
        },
        503,
    )
