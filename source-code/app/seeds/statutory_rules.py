from datetime import date

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
    Retire the obsolete Zimbabwe USD 2026 placeholder rule.

    Verified statutory rules must be installed from the statutory preset
    library.  The former seed created an active rule with PAYE disabled and
    no tax bands, which allowed payroll to produce misleading zero-PAYE
    records.  This migration-style seed is intentionally idempotent: it
    deactivates that exact legacy placeholder when present and never creates
    statutory values that have not been verified.
    """

    existing_rule = StatutoryRuleSet.query.filter_by(
        name=DEFAULT_RULE_NAME,
        currency=DEFAULT_CURRENCY,
        effective_from=DEFAULT_EFFECTIVE_DATE,
    ).first()

    if existing_rule is None:
        return {
            "created": False,
            "message": (
                "No obsolete statutory placeholder was found. "
                "Install a verified rule from the statutory preset "
                "library before processing payroll."
            ),
            "rule_set": None,
        }

    is_legacy_placeholder = (
        not existing_rule.paye_enabled
        and not existing_rule.tax_bands
        and existing_rule.source_preset_id is None
        and existing_rule.source_preset_key is None
        and not existing_rule.imported_from_library
    )

    if not is_legacy_placeholder:
        return {
            "created": False,
            "message": (
                "Existing statutory rule was preserved because it is not "
                "the obsolete placeholder: "
                f"{existing_rule.display_name}"
            ),
            "rule_set": existing_rule,
        }

    if not existing_rule.is_active:
        return {
            "created": False,
            "message": (
                "Obsolete statutory placeholder is already inactive: "
                f"{existing_rule.display_name}"
            ),
            "rule_set": existing_rule,
        }

    try:
        existing_rule.is_active = False
        db.session.commit()

    except SQLAlchemyError as error:
        db.session.rollback()

        raise StatutoryRuleSeedError(
            "The obsolete statutory placeholder could not be deactivated."
        ) from error

    return {
        "created": False,
        "message": (
            "Deactivated obsolete statutory placeholder: "
            f"{existing_rule.display_name}. Install a verified rule from "
            "the statutory preset library before processing payroll."
        ),
        "rule_set": existing_rule,
    }
