"""Safety checks for the integration-test database."""

from sqlalchemy import text


def test_database_fixture_uses_dedicated_database(
    database,
):
    """Ensure integration tests never use development data."""

    database_name = database.session.execute(
        text("SELECT current_database()")
    ).scalar_one()

    assert database_name == "buyoh_payroll_test"
