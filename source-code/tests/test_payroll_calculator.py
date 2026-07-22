from decimal import Decimal

import pytest

from app.services.payroll_calculator import (
    PayrollCalculator,
    money,
)


def test_money_converts_value_to_two_decimal_places():
    assert money("100") == Decimal("100.00")
    assert money("25.5") == Decimal("25.50")


def test_money_rounds_using_standard_payroll_rounding():
    assert money("10.125") == Decimal("10.13")
    assert money("10.124") == Decimal("10.12")


def test_payroll_calculation_for_salary_below_nssa_ceiling():
    result = PayrollCalculator(
        basic_salary="500.00",
    ).calculate()

    assert result.basic_salary == Decimal("500.00")
    assert result.gross_pay == Decimal("500.00")
    assert result.nssa == Decimal("22.50")
    assert result.employer_nssa == Decimal("22.50")
    assert result.paye == Decimal("0.00")
    assert result.aids_levy == Decimal("0.00")
    assert result.total_deductions == Decimal("22.50")
    assert result.net_pay == Decimal("477.50")
    assert result.employer_cost == Decimal("522.50")


def test_payroll_calculation_at_nssa_ceiling():
    result = PayrollCalculator(
        basic_salary="700.00",
    ).calculate()

    assert result.nssa == Decimal("31.50")
    assert result.employer_nssa == Decimal("31.50")
    assert result.net_pay == Decimal("668.50")
    assert result.employer_cost == Decimal("731.50")


def test_payroll_calculation_above_nssa_ceiling():
    result = PayrollCalculator(
        basic_salary="1500.00",
    ).calculate()

    assert result.gross_pay == Decimal("1500.00")
    assert result.nssa == Decimal("31.50")
    assert result.employer_nssa == Decimal("31.50")
    assert result.total_deductions == Decimal("31.50")
    assert result.net_pay == Decimal("1468.50")
    assert result.employer_cost == Decimal("1531.50")


def test_gross_pay_includes_overtime_and_allowances():
    result = PayrollCalculator(
        basic_salary="800.00",
        overtime_amount="100.00",
        allowances_total="50.00",
    ).calculate()

    assert result.basic_salary == Decimal("800.00")
    assert result.overtime_amount == Decimal("100.00")
    assert result.allowances_total == Decimal("50.00")
    assert result.gross_pay == Decimal("950.00")

    assert result.nssa == Decimal("31.50")
    assert result.employer_nssa == Decimal("31.50")
    assert result.net_pay == Decimal("918.50")
    assert result.employer_cost == Decimal("981.50")


def test_other_deductions_reduce_net_pay():
    result = PayrollCalculator(
        basic_salary="900.00",
        other_deductions_total="100.00",
    ).calculate()

    assert result.nssa == Decimal("31.50")
    assert result.other_deductions_total == Decimal("100.00")
    assert result.total_deductions == Decimal("131.50")
    assert result.net_pay == Decimal("768.50")
    assert result.employer_cost == Decimal("931.50")


def test_paye_is_zero_while_disabled():
    result = PayrollCalculator(
        basic_salary="2000.00",
    ).calculate()

    assert result.paye == Decimal("0.00")
    assert result.aids_levy == Decimal("0.00")


def test_aids_levy_calculation_method():
    calculator = PayrollCalculator(
        basic_salary="1000.00",
    )

    assert calculator.calculate_aids_levy(
        Decimal("100.00")
    ) == Decimal("3.00")


@pytest.mark.parametrize(
    "field_name, arguments",
    [
        (
            "basic salary",
            {"basic_salary": "-1.00"},
        ),
        (
            "overtime amount",
            {
                "basic_salary": "500.00",
                "overtime_amount": "-1.00",
            },
        ),
        (
            "allowances",
            {
                "basic_salary": "500.00",
                "allowances_total": "-1.00",
            },
        ),
        (
            "other deductions",
            {
                "basic_salary": "500.00",
                "other_deductions_total": "-1.00",
            },
        ),
    ],
)
def test_negative_inputs_are_rejected(
    field_name,
    arguments,
):
    with pytest.raises(
        ValueError,
        match=f"{field_name.capitalize()} cannot be negative",
    ):
        PayrollCalculator(**arguments)


def test_deductions_cannot_exceed_gross_pay():
    calculator = PayrollCalculator(
        basic_salary="100.00",
        other_deductions_total="200.00",
    )

    with pytest.raises(
        ValueError,
        match="Payroll deductions cannot exceed gross pay",
    ):
        calculator.calculate()


def test_none_optional_values_are_treated_as_zero():
    result = PayrollCalculator(
        basic_salary="500.00",
        overtime_amount=None,
        allowances_total=None,
        other_deductions_total=None,
    ).calculate()

    assert result.overtime_amount == Decimal("0.00")
    assert result.allowances_total == Decimal("0.00")
    assert result.other_deductions_total == Decimal("0.00")
    assert result.gross_pay == Decimal("500.00")

