"""Regression checks for Python 3.14-compatible UTC handling."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.time_utils import legacy_utc_now


def test_legacy_utc_now_preserves_naive_utc_database_contract():
    before = datetime.now(UTC).replace(tzinfo=None)
    actual = legacy_utc_now()
    after = datetime.now(UTC).replace(tzinfo=None)

    assert actual.tzinfo is None
    assert before <= actual <= after
    assert after - actual < timedelta(seconds=1)


def test_application_has_no_deprecated_utcnow_references():
    app_root = Path(__file__).resolve().parents[2] / "app"
    offenders = []

    for path in sorted(app_root.rglob("*.py")):
        if "datetime.utcnow" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(app_root.parent)))

    assert offenders == []
