"""Environment-driven Flask configuration."""

import os
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv()


def env_bool(name, default=False):
    """Read a strict, case-insensitive boolean environment value."""

    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


def database_uri():
    """Build the database URI without embedding credentials in source."""

    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    names = (
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
    )
    values = {name: os.getenv(name) for name in names}
    if not all(values.values()):
        return None

    return (
        "postgresql+psycopg2://"
        f"{values['DATABASE_USER']}:{values['DATABASE_PASSWORD']}@"
        f"{values['DATABASE_HOST']}:{values['DATABASE_PORT']}/"
        f"{values['DATABASE_NAME']}"
    )


class Config:
    """Secure defaults shared by development and production."""

    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    DEBUG = env_bool("FLASK_DEBUG", False)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = env_bool(
        "SESSION_COOKIE_SECURE",
        APP_ENV == "production",
    )
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https" if APP_ENV == "production" else "http"

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = env_bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
