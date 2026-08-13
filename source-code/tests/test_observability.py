"""Structured logging, request correlation and safe-error tests."""

import json
import logging

from flask import Flask, request

from app.extensions import db
from app.observability import (
    JsonFormatter,
    configure_logging,
    register_error_handlers,
    register_request_observability,
)


def build_app():
    app = Flask(
        __name__,
        template_folder="../app/templates",
    )
    app.config.update(
        TESTING=False,
        PROPAGATE_EXCEPTIONS=False,
        LOG_LEVEL="INFO",
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    db.init_app(app)
    configure_logging(app)
    register_request_observability(app)
    register_error_handlers(app)

    @app.get("/ok")
    def ok():
        return "ok"

    @app.get("/fail")
    def fail():
        raise RuntimeError("database password must remain private")

    return app


def test_json_formatter_emits_machine_readable_context():
    record = logging.LogRecord(
        "buyoh",
        logging.INFO,
        __file__,
        1,
        "request_completed",
        (),
        None,
    )
    record.request_id = "request-1"
    record.status_code = 200

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "request_completed"
    assert payload["request_id"] == "request-1"
    assert payload["status_code"] == 200
    assert payload["timestamp"].endswith("Z")


def test_request_id_is_generated_and_returned():
    response = build_app().test_client().get("/ok")

    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 32


def test_safe_incoming_request_id_is_preserved():
    response = build_app().test_client().get(
        "/ok",
        headers={"X-Request-ID": "edge-request_123"},
    )

    assert response.headers["X-Request-ID"] == "edge-request_123"


def test_unsafe_incoming_request_id_is_replaced():
    response = build_app().test_client().get(
        "/ok",
        headers={"X-Request-ID": "invalid request id"},
    )

    assert response.headers["X-Request-ID"] != "invalid request id"
    assert len(response.headers["X-Request-ID"]) == 32


def test_not_found_is_friendly_and_correlated():
    response = build_app().test_client().get("/missing")
    body = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "Page not found" in body
    assert response.headers["X-Request-ID"] in body


def test_internal_error_hides_exception_details():
    response = build_app().test_client().get("/fail")
    body = response.get_data(as_text=True).lower()

    assert response.status_code == 500
    assert "something went wrong" in body
    assert response.headers["X-Request-ID"] in body
    assert "database password" not in body
    assert "traceback" not in body


def test_oversized_request_has_safe_friendly_response():
    app = build_app()
    app.config["MAX_CONTENT_LENGTH"] = 4

    @app.post("/upload")
    def upload():
        return str(len(request.get_data()))

    response = app.test_client().post("/upload", data="too large")

    assert response.status_code == 413
    assert "Upload too large" in response.get_data(as_text=True)


def test_invalid_log_level_fails_fast():
    app = Flask(__name__)
    app.config["LOG_LEVEL"] = "LOUD"

    try:
        configure_logging(app)
    except RuntimeError as error:
        assert "Invalid LOG_LEVEL" in str(error)
    else:
        raise AssertionError("Invalid logging level was accepted")
