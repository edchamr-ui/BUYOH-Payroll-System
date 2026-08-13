"""Security-focused configuration regression tests."""

from flask import Flask
import pytest

from app import create_app
from app.security import register_security_headers, validate_runtime_config


def config_app(**overrides):
    app = Flask(__name__)
    app.config.update(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="x" * 48,
        SQLALCHEMY_DATABASE_URI="postgresql://example.invalid/payroll",
        SESSION_COOKIE_SECURE=True,
        TESTING=False,
    )
    app.config.update(overrides)
    return app


def test_application_uses_secure_cookie_defaults():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert app.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"SECRET_KEY": None}, "SECRET_KEY is required"),
        ({"SECRET_KEY": "short"}, "at least 32"),
        ({"SQLALCHEMY_DATABASE_URI": None}, "Database configuration"),
        ({"SESSION_COOKIE_SECURE": False}, "SESSION_COOKIE_SECURE"),
        ({"DEBUG": True}, "Debug mode"),
        ({"APP_ENV": "unknown"}, "APP_ENV must be"),
    ),
)
def test_production_rejects_unsafe_configuration(overrides, message):
    app = config_app(**overrides)

    with pytest.raises(RuntimeError, match=message):
        validate_runtime_config(app)


def test_production_accepts_explicit_secure_configuration():
    validate_runtime_config(config_app())


def test_security_headers_are_added_without_overwriting_application_values():
    app = config_app(TESTING=True)
    register_security_headers(app)

    @app.route("/")
    def index():
        return "ok", 200, {"X-Frame-Options": "DENY"}

    response = app.test_client().get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == (
        "strict-origin-when-cross-origin"
    )
    assert response.headers["Strict-Transport-Security"].startswith(
        "max-age="
    )
