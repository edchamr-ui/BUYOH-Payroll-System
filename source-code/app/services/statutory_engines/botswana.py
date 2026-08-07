"""
Botswana statutory payroll engine.
"""

from decimal import Decimal

from app.services.statutory_engines.base import (
    StatutoryEngineValidation,
)
from app.services.statutory_engines.progressive import (
    ProgressivePayeEngine,
)

ZERO = Decimal("0.00")


class BotswanaStatutoryEngine(ProgressivePayeEngine):
    """
    Botswana PAYE statutory engine.

    Current implementation:

    ✔ Progressive PAYE
    ✔ No employee social contribution
    ✔ No employer social contribution
    ✔ No payroll levy

    Future versions can introduce
    Botswana-specific statutory deductions
    without changing PayrollService.
    """

    engine_key = "BOTSWANA_PAYE"

    country_code = "BW"

    aliases = (
        "BOTSWANA",
        "BW",
        "BW_PAYE",
    )

    contribution_labels = {
        "employee": "Employee Contribution",
        "employer": "Employer Contribution",
        "levy": "Payroll Levy",
    }

    @classmethod
    def validate_configuration(
        cls,
        statutory_config,
    ):
        """
        Validate Botswana statutory configuration.
        """

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

            if currency != "BWP":
                errors.append(
                    "Botswana engine requires BWP currency."
                )

        return StatutoryEngineValidation(
            engine_key=cls.engine_key,
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def calculate_employee_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
    ):
        """
        Botswana currently has no
        employee statutory contribution.
        """

        return {}

    def calculate_employer_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
    ):
        """
        Botswana currently has no
        employer statutory contribution.
        """

        return {}

    def calculate_levies(
        self,
        *,
        paye,
        gross_pay,
        statutory_config,
    ):
        """
        Botswana currently has
        no payroll levy.
        """

        return {}
