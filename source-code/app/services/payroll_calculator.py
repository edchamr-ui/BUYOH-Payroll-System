from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.services.statutory_config import (
    USD_STATUTORY_CONFIG,
    StatutoryConfiguration,
)


MONEY_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    """Convert a value to a two-decimal Decimal."""

    if value is None:
        value = ZERO

    return Decimal(str(value)).quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


@dataclass(frozen=True)
class PayrollCalculation:
    """Immutable payroll result for one employee."""

    basic_salary: Decimal
    overtime_amount: Decimal
    allowances_total: Decimal
    non_cash_benefits_total: Decimal
    allowable_deductions_total: Decimal
    gross_pay: Decimal

    nssa: Decimal
    employer_nssa: Decimal
    paye: Decimal
    aids_levy: Decimal

    other_deductions_total: Decimal
    total_deductions: Decimal
    net_pay: Decimal

    employer_cost: Decimal


class PayrollCalculator:
    """Calculate payroll values for one employee."""

    def __init__(
        self,
        basic_salary,
        overtime_amount=ZERO,
        allowances_total=ZERO,
        taxable_allowances_total=None,
        non_cash_benefits_total=ZERO,
        allowable_deductions_total=ZERO,
        other_deductions_total=ZERO,
        statutory_config: StatutoryConfiguration = (
            USD_STATUTORY_CONFIG
        ),
    ):
        self.basic_salary = money(basic_salary)
        self.overtime_amount = money(overtime_amount)
        self.allowances_total = money(allowances_total)
        self.taxable_allowances_total = money(
            allowances_total
            if taxable_allowances_total is None
            else taxable_allowances_total
        )
        self.non_cash_benefits_total = money(
            non_cash_benefits_total
        )
        self.allowable_deductions_total = money(
            allowable_deductions_total
        )

        self.other_deductions_total = money(
            other_deductions_total
        )

        self.statutory_config = statutory_config

        self._validate_inputs()

    def _validate_inputs(self):
        """Reject invalid negative payroll inputs."""

        values = {
            "basic salary": self.basic_salary,
            "overtime amount": self.overtime_amount,
            "allowances": self.allowances_total,
            "taxable allowances": self.taxable_allowances_total,
            "non-cash benefits": self.non_cash_benefits_total,
            "allowable deductions": self.allowable_deductions_total,
            "other deductions": self.other_deductions_total,
        }

        for field_name, value in values.items():
            if value < ZERO:
                raise ValueError(
                    f"{field_name.capitalize()} cannot be negative."
                )

    def calculate_nssa_insurable_earnings(
        self,
        gross_pay,
    ):
        """Apply the configured NSSA earnings ceiling."""

        ceiling = money(
            self.statutory_config.nssa_monthly_ceiling
        )

        return min(
            money(gross_pay),
            ceiling,
        )

    def calculate_employee_nssa(
        self,
        gross_pay,
    ):
        """Calculate the employee NSSA contribution."""

        insurable_earnings = (
            self.calculate_nssa_insurable_earnings(
                gross_pay
            )
        )

        return money(
            insurable_earnings
            * self.statutory_config.nssa_employee_rate
        )

    def calculate_employer_nssa(
        self,
        gross_pay,
    ):
        """Calculate the employer NSSA contribution."""

        insurable_earnings = (
            self.calculate_nssa_insurable_earnings(
                gross_pay
            )
        )

        return money(
            insurable_earnings
            * self.statutory_config.nssa_employer_rate
        )

    def calculate_paye(
        self,
        taxable_income,
    ):
        """
        Calculate PAYE progressively across configured bands.

        Each band taxes only the portion of taxable income that
        falls inside that band's range.
        """

        taxable_income = money(taxable_income)

        if not self.statutory_config.paye_enabled:
            return ZERO

        tax_bands = self.statutory_config.tax_bands

        if not tax_bands:
            raise ValueError(
                "PAYE is enabled, but no tax bands "
                "have been configured."
            )

        paye = ZERO

        for band in sorted(
            tax_bands,
            key=lambda item: item.band_order,
        ):
            lower_limit = money(
                band.lower_limit
            )

            upper_limit = (
                money(band.upper_limit)
                if band.upper_limit is not None
                else None
            )

            if taxable_income <= lower_limit:
                continue

            taxable_upper_bound = taxable_income

            if upper_limit is not None:
                taxable_upper_bound = min(
                    taxable_income,
                    upper_limit,
                )

            taxable_portion = money(
                taxable_upper_bound
                - lower_limit
            )

            if taxable_portion <= ZERO:
                continue

            paye += (
                taxable_portion
                * band.rate
            )

        return money(paye)

    def calculate_aids_levy(
        self,
        paye,
    ):
        """Calculate the AIDS levy as a percentage of PAYE."""

        return money(
            money(paye)
            * self.statutory_config.aids_levy_rate
        )

    def calculate(self):
        """Return the complete payroll calculation."""

        gross_pay = money(
            self.basic_salary
            + self.overtime_amount
            + self.allowances_total
        )

        nssa = self.calculate_employee_nssa(
            gross_pay
        )

        employer_nssa = (
            self.calculate_employer_nssa(
                gross_pay
            )
        )

        taxable_income = money(max(
            ZERO,
            self.basic_salary
            + self.overtime_amount
            + self.taxable_allowances_total
            + self.non_cash_benefits_total
            - nssa
            - self.allowable_deductions_total,
        ))

        paye = money(
            self.calculate_paye(
                taxable_income
            )
        )

        aids_levy = (
            self.calculate_aids_levy(
                paye
            )
        )

        total_deductions = money(
            nssa
            + paye
            + aids_levy
            + self.other_deductions_total
        )

        net_pay = money(gross_pay - total_deductions)

        if net_pay < ZERO:
            raise ValueError(
                "Payroll deductions cannot exceed gross pay."
            )

        employer_cost = money(
            gross_pay + employer_nssa
        )

        return PayrollCalculation(
            basic_salary=self.basic_salary,
            overtime_amount=self.overtime_amount,
            allowances_total=self.allowances_total,
            non_cash_benefits_total=self.non_cash_benefits_total,
            allowable_deductions_total=self.allowable_deductions_total,
            gross_pay=gross_pay,
            nssa=nssa,
            employer_nssa=employer_nssa,
            paye=paye,
            aids_levy=aids_levy,
            other_deductions_total=(
                self.other_deductions_total
            ),
            total_deductions=(
                total_deductions
            ),
            net_pay=net_pay,
            employer_cost=employer_cost,
        )
