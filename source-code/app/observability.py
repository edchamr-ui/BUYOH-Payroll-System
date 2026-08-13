"""Structured request logging and production-safe error handling."""

import json
import logging
import re
import sys
import time
from uuid import uuid4

from flask import g, render_template, request

from app.extensions import db


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class JsonFormatter(logging.Formatter):
    """Render one machine-readable JSON object per log record."""

    converter = time.gmtime

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "remote_addr",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    """Configure predictable stdout logging for process supervisors."""

    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise RuntimeError(f"Invalid LOG_LEVEL: {level_name}")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    app.logger.propagate = False


def request_id_from_header():
    """Accept a safe caller ID or create a new opaque request ID."""

    supplied = request.headers.get(REQUEST_ID_HEADER, "")
    if REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return uuid4().hex


def register_request_observability(app):
    """Correlate and log requests without logging query strings or bodies."""

    @app.before_request
    def begin_request():
        g.request_id = request_id_from_header()
        g.request_started = time.monotonic()

    @app.after_request
    def finish_request(response):
        request_id = getattr(g, "request_id", uuid4().hex)
        started = getattr(g, "request_started", time.monotonic())
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        app.logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "remote_addr": request.remote_addr,
            },
        )
        return response


def register_error_handlers(app):
    """Return friendly errors while retaining full server-side diagnostics."""

    def error_page(template, status_code):
        return (
            render_template(
                template,
                request_id=getattr(g, "request_id", None),
            ),
            status_code,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return error_page("errors/404.html", 404)

    @app.errorhandler(413)
    def request_too_large(_error):
        return error_page("errors/413.html", 413)

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        original = getattr(error, "original_exception", None) or error
        app.logger.exception(
            "unhandled_request_error",
            exc_info=(
                type(original),
                original,
                original.__traceback__,
            ),
            extra={"request_id": getattr(g, "request_id", None)},
        )
        return error_page("errors/500.html", 500)
