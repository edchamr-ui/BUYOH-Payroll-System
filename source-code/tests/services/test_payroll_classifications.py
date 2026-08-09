"""Regression tests for classified Botswana payroll inputs."""

from decimal import Decimal

from app.services.payroll_calculator import PayrollCalculator
from app.services.statutory_config import StatutoryConfiguration


ZERO = Decimal("0.00")


def _configuration():
    return StatutoryConfiguration(
        currency="BWP",
        nssa_employee_rate=ZERO,
        nssa_employer_rate=ZERO,
        nssa_monthly_ceiling=ZERO,
        aids_levy_rate=ZERO,
        paye_enabled=False,
        tax_bands=(),
    )


def test_non_cash_benefit_does_not_inflate_take_home_pay():
    result = PayrollCalculator(
        basic_salary=Decimal("10000"),
        allowances_total=Decimal("500"),
        taxable_allowances_total=Decimal("500"),
        non_cash_benefits_total=Decimal("1000"),
        statutory_config=_configuration(),
    ).calculate()

    assert result.gross_pay == Decimal("10500.00")
    assert result.net_pay == Decimal("10500.00")
    assert result.non_cash_benefits_total == Decimal("1000.00")


def test_allowable_deduction_is_reported_separately():
    result = PayrollCalculator(
        basic_salary=Decimal("10000"),
        other_deductions_total=Decimal("600"),
        allowable_deductions_total=Decimal("600"),
        statutory_config=_configuration(),
    ).calculate()

    assert result.allowable_deductions_total == Decimal("600.00")
    assert result.other_deductions_total == Decimal("600.00")
    assert result.net_pay == Decimal("9400.00")


def test_non_taxable_cash_allowance_remains_cash_earnings():
    result = PayrollCalculator(
        basic_salary=Decimal("10000"),
        allowances_total=Decimal("750"),
        taxable_allowances_total=ZERO,
        statutory_config=_configuration(),
    ).calculate()

    assert result.gross_pay == Decimal("10750.00")
    assert result.net_pay == Decimal("10750.00")
