"""Shared pytest fixtures for database integration tests."""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db
from config import Config


TEST_DATABASE_NAME = "buyoh_payroll_test"


def build_test_database_uri():
    """Build and validate the dedicated test database URI."""

    source_url = make_url(
        Config.SQLALCHEMY_DATABASE_URI
    )

    test_url = source_url.set(
        database=TEST_DATABASE_NAME
    )

    if test_url.database != TEST_DATABASE_NAME:
        raise RuntimeError(
            "Refusing to use an unsafe test database."
        )

    return test_url.render_as_string(
        hide_password=False
    )


def verify_test_database():
    """Confirm the active connection targets the test database."""

    database_name = db.session.execute(
        text("SELECT current_database()")
    ).scalar_one()

    if database_name != TEST_DATABASE_NAME:
        raise RuntimeError(
            "Refusing to modify database "
            f"{database_name!r}; expected "
            f"{TEST_DATABASE_NAME!r}."
        )


@pytest.fixture
def app():
    """Create an isolated Flask application and database schema."""

    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_DATABASE_URI": (
            build_test_database_uri()
        ),
    })

    with application.app_context():
        verify_test_database()

        db.drop_all()
        db.create_all()

        yield application

        db.session.remove()
        verify_test_database()
        db.drop_all()


@pytest.fixture
def database(app):
    """Provide the initialized test database extension."""

    return db


@pytest.fixture
def client(app):
    """Provide a Flask test client."""

    return app.test_client()
