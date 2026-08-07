"""Zambia statutory payroll engine."""

from decimal import Decimal

from app.services.statutory_engines.base import (
    StatutoryEngineValidation,
)
from app.services.statutory_engines.progressive import (
    ProgressivePayeEngine,
)


ZERO = Decimal("0.00")


class ZambiaStatutoryEngine(ProgressivePayeEngine):
    """
    Calculate Zambia PAYE and NAPSA contributions.

    Current compatibility mapping:
        PayrollCalculation.nssa          -> employee NAPSA
        PayrollCalculation.employer_nssa -> employer NAPSA
        PayrollCalculation.aids_levy     -> zero
    """

    engine_key = "ZAMBIA_PROGRESSIVE"
    country_code = "ZM"

    aliases = (
        "ZAMBIA",
        "ZM",
        "ZM_PROGRESSIVE",
        "ZAMBIA_PAYE",
    )

    contribution_labels = {
        "employee": "NAPSA Employee",
        "employer": "NAPSA Employer",
        "levy": "Statutory Levy",
    }

    @classmethod
    def validate_configuration(
        cls,
        statutory_config,
    ):
        shared = super().validate_configuration(
            statutory_config
        )

        errors = list(shared.errors)
        warnings = list(shared.warnings)

        if statutory_config is not None:
            currency = str(
                getattr(
                    statutory_config,
                    "currency",
                    "",
                )
                or ""
            ).strip().upper()

            if currency != "ZMW":
                errors.append(
                    "The Zambia engine requires ZMW currency."
                )

            levy_rate = Decimal(
                str(
                    getattr(
                        statutory_config,
                        "aids_levy_rate",
                        ZERO,
                    )
                    or ZERO
                )
            )

            if levy_rate != ZERO:
                warnings.append(
                    "A levy rate is configured for Zambia. "
                    "Confirm that it is intentional."
                )

        return StatutoryEngineValidation(
            engine_key=cls.engine_key,
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def calculate_levies(
        self,
        *,
        paye,
        gross_pay,
        statutory_config,
    ):
        """Zambia currently applies no PAYE-based levy here."""

        return {}
