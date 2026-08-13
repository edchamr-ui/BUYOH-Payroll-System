"""Production configuration validation and baseline response hardening."""

from flask import current_app


FORBIDDEN_SECRETS = {
    "change-me",
    "dev",
    "development",
    "secret",
    "secret-key",
}


def validate_runtime_config(app):
    """Fail fast when required configuration is missing or unsafe."""

    if app.config.get("TESTING"):
        return

    secret = str(app.config.get("SECRET_KEY") or "")
    database = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    production = app.config.get("APP_ENV") == "production"

    if app.config.get("APP_ENV") not in {
        "development",
        "testing",
        "production",
    }:
        raise RuntimeError(
            "APP_ENV must be development, testing, or production."
        )

    if not database:
        raise RuntimeError(
            "Database configuration is required. Set DATABASE_URL or all "
            "DATABASE_* variables."
        )
    if not secret:
        raise RuntimeError("SECRET_KEY is required.")
    if production:
        if len(secret) < 32 or secret.lower() in FORBIDDEN_SECRETS:
            raise RuntimeError(
                "Production SECRET_KEY must be a random value of at least "
                "32 characters."
            )
        if not app.config.get("SESSION_COOKIE_SECURE"):
            raise RuntimeError(
                "Production requires SESSION_COOKIE_SECURE=true."
            )
        if app.config.get("DEBUG"):
            raise RuntimeError("Debug mode cannot be enabled in production.")


def register_security_headers(app):
    """Apply low-risk browser security headers to every response."""

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if current_app.config.get("APP_ENV") == "production":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
