"""Reusable progressive PAYE engine implementation."""

from app.services.payroll_calculator import (
    PayrollCalculator,
    money,
)
from app.services.statutory_engines.base import (
    BaseStatutoryEngine,
    InvalidStatutoryConfigurationError,
)


class ProgressivePayeEngine(BaseStatutoryEngine):
    """
    Implement shared progressive PAYE behaviour.

    Existing database fields remain mapped through PayrollCalculator,
    preserving compatibility with current PayrollRecord columns.
    """

    def _calculator(
        self,
        *,
        basic_salary=0,
        overtime_amount=0,
        allowances_total=0,
        other_deductions_total=0,
        statutory_config,
    ):
        validation = self.validate_configuration(
            statutory_config
        )

        if not validation.valid:
            raise InvalidStatutoryConfigurationError(
                "; ".join(validation.errors)
            )

        return PayrollCalculator(
            basic_salary=basic_salary,
            overtime_amount=overtime_amount,
            allowances_total=allowances_total,
            other_deductions_total=other_deductions_total,
            statutory_config=statutory_config,
        )

    def calculate_paye(
        self,
        *,
        taxable_income,
        statutory_config,
    ):
        calculator = self._calculator(
            statutory_config=statutory_config
        )

        return calculator.calculate_paye(
            money(taxable_income)
        )

    def calculate_employee_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
    ):
        calculator = self._calculator(
            statutory_config=statutory_config
        )

        return {
            self.contribution_labels[
                "employee"
            ]: calculator.calculate_employee_nssa(
                money(gross_pay)
            )
        }

    def calculate_employer_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
    ):
        calculator = self._calculator(
            statutory_config=statutory_config
        )

        return {
            self.contribution_labels[
                "employer"
            ]: calculator.calculate_employer_nssa(
                money(gross_pay)
            )
        }

    def calculate_levies(
        self,
        *,
        paye,
        gross_pay,
        statutory_config,
    ):
        calculator = self._calculator(
            statutory_config=statutory_config
        )

        levy = calculator.calculate_aids_levy(
            money(paye)
        )

        if levy == 0:
            return {}

        return {
            self.contribution_labels["levy"]: levy
        }

    def calculate(
        self,
        *,
        basic_salary,
        overtime_amount,
        allowances_total,
        other_deductions_total,
        statutory_config,
    ):
        calculator = self._calculator(
            basic_salary=basic_salary,
            overtime_amount=overtime_amount,
            allowances_total=allowances_total,
            other_deductions_total=other_deductions_total,
            statutory_config=statutory_config,
        )

        return calculator.calculate()
