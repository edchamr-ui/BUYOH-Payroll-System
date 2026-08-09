"""
Botswana statutory payroll engine.
"""

from dataclasses import is_dataclass, replace
from decimal import Decimal
from types import SimpleNamespace

from app.services.statutory_engines.base import (
    InvalidStatutoryConfigurationError,
    StatutoryEngineValidation,
)
from app.services.statutory_config import TaxBandConfiguration
from app.services.payroll_calculator import PayrollCalculator
from app.services.statutory_engines.progressive import (
    ProgressivePayeEngine,
)

ZERO = Decimal("0.00")

NON_RESIDENT_MONTHLY_BANDS = (
    TaxBandConfiguration(
        1, Decimal("0"), Decimal("7000"), Decimal("0.05")
    ),
    TaxBandConfiguration(
        2, Decimal("7000"), Decimal("10000"), Decimal("0.125")
    ),
    TaxBandConfiguration(
        3, Decimal("10000"), Decimal("13000"), Decimal("0.1875")
    ),
    TaxBandConfiguration(
        4, Decimal("13000"), Decimal("33333"), Decimal("0.25")
    ),
    TaxBandConfiguration(
        5, Decimal("33333"), None, Decimal("0.275")
    ),
)


class BotswanaStatutoryEngine(ProgressivePayeEngine):
    """
    Botswana PAYE statutory engine.

    Current production scope:

    - Resident and non-resident employees paid monthly
    - Progressive PAYE for the 2026/27 tax year
    - No employee or employer social contribution
    - No payroll levy

    Residency must be explicitly supplied by the employee record and
    is never inferred from nationality or currency.
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

            paye_enabled = bool(
                getattr(statutory_config, "paye_enabled", False)
            )
            tax_bands = tuple(
                getattr(statutory_config, "tax_bands", ()) or ()
            )

            if not paye_enabled:
                errors.append(
                    "Botswana resident PAYE must be enabled."
                )

            residency = str(
                getattr(statutory_config, "tax_residency", "Resident")
                or "Resident"
            ).strip().lower()

            if residency not in {"resident", "non-resident"}:
                errors.append(
                    "Botswana tax residency must be Resident or Non-Resident."
                )

            if len(tax_bands) != 6:
                errors.append(
                    "Botswana resident monthly PAYE requires exactly "
                    "six verified tax bands."
                )

            expected_rates = (
                Decimal("0.000000"),
                Decimal("0.050000"),
                Decimal("0.125000"),
                Decimal("0.187500"),
                Decimal("0.250000"),
                Decimal("0.275000"),
            )

            actual_rates = tuple(
                Decimal(str(getattr(band, "rate", ZERO)))
                for band in sorted(
                    tax_bands,
                    key=lambda band: band.band_order,
                )
            )

            if tax_bands and actual_rates != expected_rates:
                errors.append(
                    "Botswana resident monthly PAYE rates do not match "
                    "the verified BURS 2026/27 table."
                )

        return StatutoryEngineValidation(
            engine_key=cls.engine_key,
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _is_non_resident(statutory_config):
        return str(
            getattr(statutory_config, "tax_residency", "Resident")
            or "Resident"
        ).strip().lower() == "non-resident"

    @staticmethod
    def _with_non_resident_bands(statutory_config):
        if is_dataclass(statutory_config):
            return replace(
                statutory_config,
                tax_bands=NON_RESIDENT_MONTHLY_BANDS,
            )

        values = dict(vars(statutory_config))
        values["tax_bands"] = NON_RESIDENT_MONTHLY_BANDS
        return SimpleNamespace(**values)

    def calculate_paye(self, *, taxable_income, statutory_config):
        validation = self.validate_configuration(statutory_config)
        if not validation.valid:
            raise InvalidStatutoryConfigurationError(
                "; ".join(validation.errors)
            )

        if not self._is_non_resident(statutory_config):
            return super().calculate_paye(
                taxable_income=taxable_income,
                statutory_config=statutory_config,
            )

        non_resident_config = self._with_non_resident_bands(
            statutory_config
        )
        return PayrollCalculator(
            basic_salary=0,
            statutory_config=non_resident_config,
        ).calculate_paye(taxable_income)

    def calculate(
        self,
        *,
        basic_salary,
        overtime_amount,
        allowances_total,
        other_deductions_total,
        statutory_config,
        taxable_allowances_total=None,
        non_cash_benefits_total=ZERO,
        allowable_deductions_total=ZERO,
    ):
        return PayrollCalculator(
            basic_salary=basic_salary,
            overtime_amount=overtime_amount,
            allowances_total=allowances_total,
            taxable_allowances_total=taxable_allowances_total,
            non_cash_benefits_total=non_cash_benefits_total,
            allowable_deductions_total=allowable_deductions_total,
            other_deductions_total=other_deductions_total,
            statutory_config=(
                self._with_non_resident_bands(statutory_config)
                if self._is_non_resident(statutory_config)
                else statutory_config
            ),
        ).calculate()

    def calculate_employee_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
    ):
        """
        Botswana has no configured
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
        Botswana has no configured
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
        Botswana has
        no payroll levy.
        """

        return {}
