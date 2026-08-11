"""Tests for UK director NI payroll-history integration."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.payroll_service import (
    PayrollConfigurationError,
    PayrollService,
)


@pytest.mark.parametrize(
    ("employment_date", "payment_date", "expected_week"),
    (
        (date(2020, 1, 1), date(2026, 4, 30), 1),
        (date(2026, 4, 6), date(2026, 4, 30), 1),
        (date(2026, 4, 12), date(2026, 4, 30), 1),
        (date(2026, 4, 13), date(2026, 4, 30), 2),
        (date(2026, 10, 1), date(2026, 10, 31), 26),
        (date(2027, 4, 5), date(2027, 4, 5), 53),
    ),
)
def test_director_appointment_week_uses_hmrc_tax_weeks(
    employment_date,
    payment_date,
    expected_week,
):
    assert PayrollService._uk_director_appointment_week(
        employment_date,
        payment_date,
    ) == expected_week


def test_director_appointment_week_defaults_to_full_year_without_date():
    assert PayrollService._uk_director_appointment_week(
        None,
        date(2026, 4, 30),
    ) == 1


def test_director_appointment_after_payment_is_rejected():
    with pytest.raises(
        PayrollConfigurationError,
        match="cannot be after the payment date",
    ):
        PayrollService._uk_director_appointment_week(
            date(2026, 6, 1),
            date(2026, 5, 31),
        )


@pytest.mark.parametrize(
    ("payment_date", "termination_date", "expected"),
    (
        (date(2027, 3, 31), None, True),
        (date(2027, 4, 5), None, True),
        (date(2026, 11, 30), date(2026, 11, 20), True),
        (date(2026, 11, 30), date(2026, 12, 20), False),
        (date(2026, 11, 30), None, False),
    ),
)
def test_director_final_period_detection(
    payment_date,
    termination_date,
    expected,
):
    employee = SimpleNamespace(termination_date=termination_date)
    period = SimpleNamespace(
        end_date=date(payment_date.year, payment_date.month, 30)
        if payment_date.month != 4
        else date(payment_date.year, 4, 30)
    )

    assert PayrollService._uk_director_final_pay_period(
        employee,
        period,
        payment_date,
    ) is expected


def test_uk_ytd_context_supplies_director_ni_history(monkeypatch):
    rows = [
        SimpleNamespace(
            uk_taxable_pay=Decimal("4000.00"),
            paye=Decimal("590.20"),
            gross_pay=Decimal("4100.00"),
            nssa=Decimal("244.16"),
            employer_nssa=Decimal("552.45"),
        ),
        SimpleNamespace(
            uk_taxable_pay=Decimal("4250.00"),
            paye=Decimal("640.00"),
            gross_pay=Decimal("4250.00"),
            nssa=Decimal("256.16"),
            employer_nssa=Decimal("574.95"),
        ),
    ]
    monkeypatch.setattr(
        PayrollService,
        "_uk_history_records",
        staticmethod(lambda employee_id, calculation_date: rows),
    )

    result = PayrollService._uk_ytd_context(
        employee_id=7,
        calculation_date=date(2026, 6, 30),
    )

    assert result["ni_earnings"] == Decimal("8350.00")
    assert result["employee_ni"] == Decimal("500.32")
    assert result["employer_ni"] == Decimal("1127.40")
