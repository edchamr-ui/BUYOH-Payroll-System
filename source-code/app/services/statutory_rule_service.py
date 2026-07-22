from datetime import date
from decimal import Decimal

from app.models import StatutoryRuleSet
from app.services.statutory_config import (
    StatutoryConfiguration,
    TaxBandConfiguration,
)


class StatutoryRuleServiceError(Exception):
    """Base exception for statutory-rule service failures."""


class StatutoryRuleNotFoundError(
    StatutoryRuleServiceError
):
    """Raised when no applicable statutory rule set exists."""


class MultipleStatutoryRulesError(
    StatutoryRuleServiceError
):
    """Raised when overlapping rule sets are found."""


class InvalidTaxBandConfigurationError(
    StatutoryRuleServiceError
):
    """Raised when PAYE is enabled without valid tax bands."""


class StatutoryRuleService:
    """
    Find and convert effective-dated statutory payroll rules.
    """

    @staticmethod
    def get_applicable_rule_set(
        calculation_date,
        currency="USD",
    ):
        """Return the active rules for a date and currency."""

        if not isinstance(calculation_date, date):
            raise TypeError(
                "Calculation date must be a date object."
            )

        normalized_currency = (
            str(currency).strip().upper()
        )

        if not normalized_currency:
            raise ValueError("Currency is required.")

        matching_rules = (
            StatutoryRuleSet.query
            .filter(
                StatutoryRuleSet.currency
                == normalized_currency,
                StatutoryRuleSet.is_active.is_(True),
                StatutoryRuleSet.effective_from
                <= calculation_date,
                (
                    StatutoryRuleSet.effective_to.is_(None)
                    | (
                        StatutoryRuleSet.effective_to
                        >= calculation_date
                    )
                ),
            )
            .order_by(
                StatutoryRuleSet.effective_from.desc(),
                StatutoryRuleSet.id.desc(),
            )
            .all()
        )

        if not matching_rules:
            raise StatutoryRuleNotFoundError(
                "No active statutory rule set was found "
                f"for {normalized_currency} on "
                f"{calculation_date.isoformat()}."
            )

        if len(matching_rules) > 1:
            raise MultipleStatutoryRulesError(
                "Multiple active statutory rule sets apply "
                f"to {normalized_currency} on "
                f"{calculation_date.isoformat()}. "
                "Check for overlapping effective dates."
            )

        return matching_rules[0]

    @staticmethod
    def _convert_tax_bands(rule_set):
        """Convert database tax bands into immutable values."""

        converted_bands = tuple(
            TaxBandConfiguration(
                band_order=band.band_order,
                lower_limit=Decimal(
                    str(band.lower_limit)
                ),
                upper_limit=(
                    Decimal(str(band.upper_limit))
                    if band.upper_limit is not None
                    else None
                ),
                rate=Decimal(str(band.rate)),
            )
            for band in rule_set.tax_bands
        )

        if rule_set.paye_enabled and not converted_bands:
            raise InvalidTaxBandConfigurationError(
                "PAYE is enabled, but the statutory rule "
                "set has no tax bands."
            )

        return converted_bands

    @classmethod
    def to_configuration(cls, rule_set):
        """Convert database rules into calculator configuration."""

        if rule_set is None:
            raise ValueError(
                "A statutory rule set is required."
            )

        return StatutoryConfiguration(
            currency=rule_set.currency,
            nssa_employee_rate=Decimal(
                str(rule_set.nssa_employee_rate)
            ),
            nssa_employer_rate=Decimal(
                str(rule_set.nssa_employer_rate)
            ),
            nssa_monthly_ceiling=Decimal(
                str(rule_set.nssa_monthly_ceiling)
            ),
            aids_levy_rate=Decimal(
                str(rule_set.aids_levy_rate)
            ),
            paye_enabled=bool(rule_set.paye_enabled),
            tax_bands=cls._convert_tax_bands(rule_set),
        )

    @classmethod
    def get_configuration(
        cls,
        calculation_date,
        currency="USD",
    ):
        """Return calculator-ready configuration for a date."""

        rule_set = cls.get_applicable_rule_set(
            calculation_date=calculation_date,
            currency=currency,
        )

        return cls.to_configuration(rule_set)
