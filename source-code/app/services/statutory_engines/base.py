"""Base contracts shared by every statutory payroll engine."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


ZERO = Decimal("0.00")


class StatutoryEngineError(Exception):
    """Base exception for statutory engine failures."""


class UnsupportedStatutoryEngineError(StatutoryEngineError):
    """Raised when a configured engine cannot be resolved."""


class InvalidStatutoryConfigurationError(
    StatutoryEngineError
):
    """Raised when an engine receives incomplete statutory rules."""


@dataclass(frozen=True)
class StatutoryEngineValidation:
    """Validation outcome for one engine and rule configuration."""

    engine_key: str
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


class BaseStatutoryEngine(ABC):
    """
    Common country-engine interface.

    Each engine exposes separate calculation hooks for PAYE,
    employee contributions, employer contributions and levies,
    while calculate() returns the application's existing
    PayrollCalculation object for backward compatibility.
    """

    engine_key = None
    aliases = ()
    country_code = None
    contribution_labels = {
        "employee": "Employee statutory contribution",
        "employer": "Employer statutory contribution",
        "levy": "Statutory levy",
    }

    @classmethod
    def supported_keys(cls):
        """Return every registry key accepted by this engine."""

        keys = []

        if cls.engine_key:
            keys.append(
                str(cls.engine_key).strip().upper()
            )

        keys.extend(
            str(alias).strip().upper()
            for alias in cls.aliases
            if str(alias).strip()
        )

        return tuple(dict.fromkeys(keys))

    @classmethod
    def validate_configuration(
        cls,
        statutory_config,
    ):
        """Validate shared statutory configuration requirements."""

        errors = []
        warnings = []

        if statutory_config is None:
            errors.append(
                "A statutory configuration is required."
            )

            return StatutoryEngineValidation(
                engine_key=cls.engine_key or "",
                valid=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
            )

        if not getattr(
            statutory_config,
            "currency",
            None,
        ):
            errors.append(
                "The statutory currency is required."
            )

        paye_enabled = bool(
            getattr(
                statutory_config,
                "paye_enabled",
                False,
            )
        )

        tax_bands = tuple(
            getattr(
                statutory_config,
                "tax_bands",
                (),
            )
            or ()
        )

        if paye_enabled and not tax_bands:
            errors.append(
                "PAYE is enabled, but no tax bands are configured."
            )

        employee_rate = Decimal(
            str(
                getattr(
                    statutory_config,
                    "nssa_employee_rate",
                    ZERO,
                )
                or ZERO
            )
        )

        employer_rate = Decimal(
            str(
                getattr(
                    statutory_config,
                    "nssa_employer_rate",
                    ZERO,
                )
                or ZERO
            )
        )

        ceiling = Decimal(
            str(
                getattr(
                    statutory_config,
                    "nssa_monthly_ceiling",
                    ZERO,
                )
                or ZERO
            )
        )

        if employee_rate < ZERO:
            errors.append(
                "The employee contribution rate cannot be negative."
            )

        if employer_rate < ZERO:
            errors.append(
                "The employer contribution rate cannot be negative."
            )

        if ceiling < ZERO:
            errors.append(
                "The contribution ceiling cannot be negative."
            )

        if (
            employee_rate > ZERO
            or employer_rate > ZERO
        ) and ceiling == ZERO:
            warnings.append(
                "Contribution rates are configured without an "
                "insurable-earnings ceiling."
            )

        return StatutoryEngineValidation(
            engine_key=cls.engine_key or "",
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @abstractmethod
    def calculate_paye(
        self,
        *,
        taxable_income,
        statutory_config,
    ):
        """Calculate employee income tax."""

    @abstractmethod
    def calculate_employee_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
    ):
        """Calculate employee-side statutory contributions."""

    @abstractmethod
    def calculate_employer_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
    ):
        """Calculate employer-side statutory contributions."""

    @abstractmethod
    def calculate_levies(
        self,
        *,
        paye,
        gross_pay,
        statutory_config,
    ):
        """Calculate country-specific statutory levies."""

    @abstractmethod
    def calculate(
        self,
        *,
        basic_salary,
        overtime_amount,
        allowances_total,
        other_deductions_total,
        statutory_config,
    ):
        """Return the complete backward-compatible payroll result."""
