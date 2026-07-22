from datetime import date
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import StatutoryRuleSet


DEFAULT_RULE_NAME = "Zimbabwe USD Statutory Rules"
DEFAULT_CURRENCY = "USD"
DEFAULT_EFFECTIVE_DATE = date(2026, 1, 1)


class StatutoryRuleSeedError(Exception):
    """Raised when statutory-rule seed data cannot be saved."""


def seed_statutory_rules():
    """
    Create the default Zimbabwe USD statutory rule set.

    The function is idempotent. Running it more than once will
    not create duplicate records.
    """

    existing_rule = StatutoryRuleSet.query.filter_by(
        name=DEFAULT_RULE_NAME,
        currency=DEFAULT_CURRENCY,
        effective_from=DEFAULT_EFFECTIVE_DATE,
    ).first()

    if existing_rule is not None:
        return {
            "created": False,
            "message": (
                "Statutory rule set already exists: "
                f"{existing_rule.display_name}"
            ),
            "rule_set": existing_rule,
        }

    rule_set = StatutoryRuleSet(
        name=DEFAULT_RULE_NAME,
        currency=DEFAULT_CURRENCY,
        effective_from=DEFAULT_EFFECTIVE_DATE,
        effective_to=None,
        nssa_employee_rate=Decimal("0.045000"),
        nssa_employer_rate=Decimal("0.045000"),
        nssa_monthly_ceiling=Decimal("700.00"),
        aids_levy_rate=Decimal("0.030000"),
        paye_enabled=False,
        is_active=True,
    )

    try:
        db.session.add(rule_set)
        db.session.commit()

    except SQLAlchemyError as error:
        db.session.rollback()

        raise StatutoryRuleSeedError(
            "The statutory rule set could not be created."
        ) from error

    return {
        "created": True,
        "message": (
            "Created statutory rule set: "
            f"{rule_set.display_name}"
        ),
        "rule_set": rule_set,
    }
