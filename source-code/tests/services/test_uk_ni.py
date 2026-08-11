"""Tests for UK monthly Class 1 National Insurance in 2026/27."""

from decimal import Decimal

import pytest

from app.services.statutory_engines.uk_ni import (
    calculate_employee_class_1,
    calculate_employer_class_1,
    calculate_monthly_class_1,
)


@pytest.mark.parametrize(
    ("earnings", "expected"),
    (
        ("1048", "0.00"),
        ("2000", "76.16"),
        ("4189", "251.28"),
        ("5000", "267.50"),
    ),
)
def test_category_a_employee_ni_boundaries(earnings, expected):
    assert calculate_employee_class_1(earnings, "A") == Decimal(expected)


@pytest.mark.parametrize(
    ("category", "expected"),
    (
        ("A", "267.50"),
        ("B", "74.33"),
        ("C", "0.00"),
        ("D", "79.04"),
        ("E", "74.33"),
        ("F", "267.50"),
        ("H", "267.50"),
        ("I", "74.33"),
        ("J", "79.04"),
        ("K", "0.00"),
        ("L", "79.04"),
        ("M", "267.50"),
        ("N", "267.50"),
        ("S", "0.00"),
        ("V", "267.50"),
        ("Z", "79.04"),
    ),
)
def test_employee_rates_for_every_supported_category(category, expected):
    assert calculate_employee_class_1("5000", category) == Decimal(expected)


@pytest.mark.parametrize(
    ("category", "expected"),
    (
        ("A", "687.45"),
        ("B", "687.45"),
        ("C", "687.45"),
        ("J", "687.45"),
        ("D", "437.55"),
        ("E", "437.55"),
        ("F", "437.55"),
        ("I", "437.55"),
        ("K", "437.55"),
        ("L", "437.55"),
        ("N", "437.55"),
        ("S", "437.55"),
        ("H", "121.65"),
        ("M", "121.65"),
        ("V", "121.65"),
        ("Z", "121.65"),
    ),
)
def test_employer_rates_for_every_supported_category(category, expected):
    assert calculate_employer_class_1("5000", category) == Decimal(expected)


def test_hmrc_category_m_monthly_example():
    result = calculate_monthly_class_1("5000", "M")

    assert result.employee_ni == Decimal("267.50")
    assert result.employer_ni == Decimal("121.65")


def test_rejects_unknown_category():
    with pytest.raises(ValueError, match="Unsupported UK"):
        calculate_monthly_class_1("2000", "Q")


def test_rejects_negative_earnings():
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_monthly_class_1("-1", "A")
