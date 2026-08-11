"""Tests for UK company-director Class 1 NI in 2026/27."""

from decimal import Decimal

import pytest

from app.services.statutory_engines.uk_ni import (
    calculate_director_class_1,
    director_earnings_period_weeks,
    director_thresholds,
)


def test_full_year_director_thresholds():
    thresholds = director_thresholds(1)
    assert thresholds["weeks"] == 52
    assert thresholds["primary"] == Decimal("12570.00")
    assert thresholds["secondary"] == Decimal("5000.00")
    assert thresholds["freeport"] == Decimal("25000.00")
    assert thresholds["upper_earnings"] == Decimal("50270.00")


def test_part_year_thresholds_round_up_to_whole_pound():
    thresholds = director_thresholds(27)
    assert thresholds["weeks"] == 26
    assert thresholds["primary"] == Decimal("6285")
    assert thresholds["secondary"] == Decimal("2500")
    assert thresholds["upper_earnings"] == Decimal("25135")


@pytest.mark.parametrize((("week", "expected")), ((1, 52), (2, 51), (52, 1), (53, 1)))
def test_director_earnings_period_weeks(week, expected):
    assert director_earnings_period_weeks(week) == expected


@pytest.mark.parametrize("week", (0, 54, "bad"))
def test_rejects_invalid_appointment_week(week):
    with pytest.raises(ValueError, match="appointment week"):
        director_earnings_period_weeks(week)


def test_standard_method_charges_cumulative_liability_less_prior_paid():
    first = calculate_director_class_1("10000", category="A")
    second = calculate_director_class_1(
        "10000",
        category="A",
        prior_earnings="10000",
        prior_employee_ni=first.employee_ni,
        prior_employer_ni=first.employer_ni,
    )
    assert first.employee_ni == Decimal("0.00")
    assert first.employer_ni == Decimal("750.00")
    assert second.employee_ni == Decimal("594.40")
    assert second.employer_ni == Decimal("1500.00")
    assert second.employee_ni_to_date == Decimal("594.40")
    assert second.employer_ni_to_date == Decimal("2250.00")


def test_standard_method_handles_irregular_bonus_cumulatively():
    result = calculate_director_class_1(
        "40000",
        category="A",
        prior_earnings="12000",
        prior_employee_ni="0",
        prior_employer_ni="1050",
    )
    assert result.employee_ni_to_date == Decimal("3050.60")
    assert result.employee_ni == Decimal("3050.60")
    assert result.employer_ni_to_date == Decimal("7050.00")
    assert result.employer_ni == Decimal("6000.00")


def test_alternative_method_uses_monthly_rules_before_final_period():
    result = calculate_director_class_1(
        "5000", category="M", method="ALTERNATIVE", prior_earnings="5000"
    )
    assert result.employee_ni == Decimal("267.50")
    assert result.employer_ni == Decimal("121.65")
    assert result.final_reconciliation is False


def test_alternative_method_reconciles_employee_and_employer_ni_at_year_end():
    result = calculate_director_class_1(
        "5000",
        category="A",
        method="ALTERNATIVE",
        prior_earnings="55000",
        prior_employee_ni="2942.50",
        prior_employer_ni="7561.95",
        final_pay_period=True,
    )
    assert result.earnings_to_date == Decimal("60000.00")
    assert result.employee_ni_to_date == Decimal("3210.60")
    assert result.employer_ni_to_date == Decimal("8250.00")
    assert result.employee_ni == Decimal("268.10")
    assert result.employer_ni == Decimal("688.05")
    assert result.final_reconciliation is True


def test_part_year_standard_method_uses_pro_rata_thresholds():
    result = calculate_director_class_1(
        "30000", category="A", appointment_week=27
    )
    assert result.earnings_period_weeks == 26
    assert result.employee_ni == Decimal("1605.30")
    assert result.employer_ni == Decimal("4125.00")


@pytest.mark.parametrize(
    ("category", "employee", "employer"),
    (
        ("A", "3210.60", "8250.00"),
        ("B", "892.05", "8250.00"),
        ("C", "0.00", "8250.00"),
        ("D", "948.60", "5250.00"),
        ("M", "3210.60", "1459.50"),
    ),
)
def test_annual_method_preserves_category_rates(category, employee, employer):
    result = calculate_director_class_1("60000", category=category)
    assert result.employee_ni == Decimal(employee)
    assert result.employer_ni == Decimal(employer)


def test_rejects_unknown_director_method():
    with pytest.raises(ValueError, match="director National Insurance method"):
        calculate_director_class_1("1000", method="UNKNOWN")


@pytest.mark.parametrize(
    "kwargs",
    (
        {"current_earnings": "-1"},
        {"current_earnings": "1", "prior_earnings": "-1"},
        {"current_earnings": "1", "prior_employee_ni": "-1"},
        {"current_earnings": "1", "prior_employer_ni": "-1"},
    ),
)
def test_rejects_negative_inputs(kwargs):
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_director_class_1(**kwargs)
