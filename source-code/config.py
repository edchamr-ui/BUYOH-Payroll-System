"""Application configuration for the BUYOH Payroll System."""

import os

from dotenv import load_dotenv


# Load environment variables from the project .env file.
load_dotenv()


class Config:
    """Base configuration for the BUYOH Payroll System."""

    # ==========================================
    # Flask Security
    # ==========================================

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-secret-key-change-in-production",
    )

    # ==========================================
    # PostgreSQL Database
    # ==========================================

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        (
            f"postgresql://{os.getenv('DATABASE_USER')}:"
            f"{os.getenv('DATABASE_PASSWORD')}@"
            f"{os.getenv('DATABASE_HOST', 'localhost')}:"
            f"{os.getenv('DATABASE_PORT', '5432')}/"
            f"{os.getenv('DATABASE_NAME')}"
        ),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ==========================================
    # File Uploads
    # ==========================================

    # Maximum request/upload size: 5 MB.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # ==========================================
    # Email (SMTP)
    # ==========================================

    MAIL_SERVER = os.getenv(
        "MAIL_SERVER"
    )

    MAIL_PORT = int(
        os.getenv(
            "MAIL_PORT",
            "587",
        )
    )

    MAIL_USE_TLS = (
        os.getenv(
            "MAIL_USE_TLS",
            "True",
        ).strip().lower()
        == "true"
    )

    MAIL_USE_SSL = (
        os.getenv(
            "MAIL_USE_SSL",
            "False",
        ).strip().lower()
        == "true"
    )

    MAIL_USERNAME = os.getenv(
        "MAIL_USERNAME"
    )

    MAIL_PASSWORD = os.getenv(
        "MAIL_PASSWORD"
    )

    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER"
    )
