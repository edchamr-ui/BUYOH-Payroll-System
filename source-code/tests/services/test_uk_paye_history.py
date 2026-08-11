"""Tests for persisted UK PAYE cumulative-history support."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.payroll_record import PayrollRecord
from app.services.payroll_service import PayrollService


@pytest.mark.parametrize(
    ("payment_date", "expected_month"),
    (
        (date(2026, 4, 5), 12),
        (date(2026, 4, 6), 1),
        (date(2026, 5, 5), 1),
        (date(2026, 5, 6), 2),
        (date(2027, 3, 5), 11),
        (date(2027, 3, 6), 12),
        (date(2027, 4, 5), 12),
    ),
)
def test_uk_tax_month_uses_hmrc_boundaries(payment_date, expected_month):
    assert PayrollService._uk_tax_month(payment_date) == expected_month


def test_payroll_record_exposes_uk_history_snapshot_columns():
    expected_columns = {
        "uk_tax_code",
        "uk_tax_basis",
        "uk_tax_region",
        "uk_tax_month",
        "uk_taxable_pay",
        "uk_prior_taxable_pay",
        "uk_prior_tax_paid",
    }

    assert expected_columns.issubset(PayrollRecord.__table__.columns.keys())


def test_uk_history_columns_remain_nullable_for_other_countries():
    for name in (
        "uk_tax_code",
        "uk_tax_basis",
        "uk_tax_region",
        "uk_tax_month",
        "uk_taxable_pay",
        "uk_prior_taxable_pay",
        "uk_prior_tax_paid",
    ):
        assert PayrollRecord.__table__.columns[name].nullable is True


def test_uk_ytd_context_sums_taxable_pay_and_paye(monkeypatch):
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
        SimpleNamespace(
            uk_taxable_pay=Decimal("3900.00"),
            paye=Decimal("-50.00"),
            gross_pay=Decimal("3900.00"),
            nssa=Decimal("228.16"),
            employer_nssa=Decimal("522.45"),
        ),
    ]

    monkeypatch.setattr(
        PayrollService,
        "_uk_history_records",
        staticmethod(lambda employee_id, calculation_date: rows),
    )

    result = PayrollService._uk_ytd_context(
        employee_id=7,
        calculation_date=date(2026, 7, 31),
    )

    assert result == {
        "taxable_pay": Decimal("12150.00"),
        "tax_paid": Decimal("1180.20"),
        "ni_earnings": Decimal("12250.00"),
        "employee_ni": Decimal("728.48"),
        "employer_ni": Decimal("1649.85"),
        "elapsed_payments": 3,
    }


def test_uk_ytd_context_returns_zero_without_history(monkeypatch):
    monkeypatch.setattr(
        PayrollService,
        "_uk_history_records",
        staticmethod(lambda employee_id, calculation_date: []),
    )

    result = PayrollService._uk_ytd_context(
        employee_id=7,
        calculation_date=date(2026, 4, 30),
    )

    assert result == {
        "taxable_pay": Decimal("0.00"),
        "tax_paid": Decimal("0.00"),
        "ni_earnings": Decimal("0.00"),
        "employee_ni": Decimal("0.00"),
        "employer_ni": Decimal("0.00"),
        "elapsed_payments": 0,
    }
