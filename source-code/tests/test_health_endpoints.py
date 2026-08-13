"""Operational liveness and readiness endpoint tests."""

from flask import Flask
from sqlalchemy.exc import SQLAlchemyError
from types import SimpleNamespace

from app import health
from app.health import health_bp


def health_app(monkeypatch, database_ready=True):
    app = Flask(__name__)
    app.config.update(TESTING=True)
    app.register_blueprint(health_bp)
    monkeypatch.setattr(
        "app.health.database_is_ready",
        lambda: database_ready,
    )
    return app


def test_liveness_is_public_minimal_and_not_cached(monkeypatch):
    response = health_app(monkeypatch).test_client().get("/health/live")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"
    assert "Location" not in response.headers


def test_readiness_reports_database_success(monkeypatch):
    response = health_app(monkeypatch).test_client().get("/health/ready")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "checks": {"database": "ok"},
    }
    assert response.headers["Cache-Control"] == "no-store"


def test_readiness_failure_is_safe_and_returns_service_unavailable(monkeypatch):
    response = health_app(
        monkeypatch,
        database_ready=False,
    ).test_client().get("/health/ready")

    assert response.status_code == 503
    assert response.get_json() == {
        "status": "unavailable",
        "checks": {"database": "unavailable"},
    }
    body = response.get_data(as_text=True).lower()
    assert "postgresql" not in body
    assert "password" not in body
    assert "traceback" not in body


def test_health_endpoints_reject_state_changing_methods(monkeypatch):
    client = health_app(monkeypatch).test_client()

    assert client.post("/health/live").status_code == 405
    assert client.post("/health/ready").status_code == 405


def test_database_check_executes_minimal_query(monkeypatch):
    executed = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, statement):
            executed.append(str(statement))

    class Engine:
        def connect(self):
            return Connection()

    monkeypatch.setattr(health, "db", SimpleNamespace(engine=Engine()))

    assert health.database_is_ready() is True
    assert executed == ["SELECT 1"]


def test_database_check_converts_sqlalchemy_failure_to_false(monkeypatch):
    class Engine:
        def connect(self):
            raise SQLAlchemyError("internal database details")

    monkeypatch.setattr(health, "db", SimpleNamespace(engine=Engine()))
    app = Flask(__name__)

    with app.app_context():
        assert health.database_is_ready() is False
