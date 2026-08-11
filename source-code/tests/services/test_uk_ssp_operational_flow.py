"""Operational SSP persistence, payroll and reporting tests."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.payroll_service import PayrollConfigurationError, PayrollService
from app.services.payslip_service import PayslipService


class FakeQuery:
    def __init__(self, value):
        self.value = value

    def filter_by(self, **kwargs):
        return self

    def one_or_none(self):
        return self.value


def employee(basic="3000.00"):
    return SimpleNamespace(
        id=7,
        employee_number="UK-007",
        basic_salary=Decimal(basic),
    )


def period():
    return SimpleNamespace(id=11)


def entry(**overrides):
    values = {
        "average_weekly_earnings": Decimal("500.00"),
        "qualifying_days_per_week": 5,
        "qualifying_days_sick": 3,
        "salary_withheld": Decimal("180.00"),
        "sickness_start_date": date(2026, 8, 10),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def result():
    return SimpleNamespace(
        amount=Decimal("73.95"),
        average_weekly_earnings=Decimal("500.00"),
        weekly_rate=Decimal("123.25"),
        qualifying_days_per_week=5,
        qualifying_days_sick=3,
        payable_qualifying_days=3,
        prior_paid_qualifying_days=0,
    )


def configure(monkeypatch, ssp_entry):
    import app.services.payroll_service as payroll_service_module

    fake_model = SimpleNamespace(query=FakeQuery(ssp_entry))

    monkeypatch.setattr(
        payroll_service_module,
        "PayrollSSPInput",
        fake_model,
    )
    monkeypatch.setattr(
        PayrollService,
        "_uk_prior_ssp_paid_days",
        classmethod(lambda cls, employee_id, calculation_date: 0),
    )

def test_no_input_preserves_contractual_salary(monkeypatch):
    configure(monkeypatch, None)
    amount, normal_pay, snapshot = PayrollService._uk_ssp_snapshot(
        employee=employee(),
        period=period(),
        statutory_engine=SimpleNamespace(),
        statutory_config=SimpleNamespace(),
        calculation_date=date(2026, 8, 31),
    )
    assert amount == Decimal("0.00")
    assert normal_pay == Decimal("3000.00")
    assert snapshot == {}


def test_ssp_replaces_withheld_salary_without_double_payment(monkeypatch):
    configure(monkeypatch, entry())
    engine = SimpleNamespace(calculate_statutory_sick_pay=lambda **kwargs: result())
    amount, normal_pay, snapshot = PayrollService._uk_ssp_snapshot(
        employee=employee(),
        period=period(),
        statutory_engine=engine,
        statutory_config=SimpleNamespace(),
        calculation_date=date(2026, 8, 31),
    )
    assert normal_pay == Decimal("2820.00")
    assert amount == Decimal("73.95")
    assert normal_pay + amount == Decimal("2893.95")
    assert snapshot["uk_ssp_amount"] == Decimal("73.95")
    assert snapshot["uk_ssp_salary_withheld"] == Decimal("180.00")


def test_snapshot_contains_audit_inputs(monkeypatch):
    configure(monkeypatch, entry())
    engine = SimpleNamespace(calculate_statutory_sick_pay=lambda **kwargs: result())
    _, _, snapshot = PayrollService._uk_ssp_snapshot(
        employee=employee(), period=period(), statutory_engine=engine,
        statutory_config=SimpleNamespace(), calculation_date=date(2026, 8, 31),
    )
    assert snapshot["uk_ssp_average_weekly_earnings"] == Decimal("500.00")
    assert snapshot["uk_ssp_weekly_rate"] == Decimal("123.25")
    assert snapshot["uk_ssp_payable_days"] == 3
    assert snapshot["uk_ssp_sickness_start_date"] == date(2026, 8, 10)


def test_salary_withheld_cannot_exceed_contractual_salary(monkeypatch):
    configure(monkeypatch, entry(salary_withheld=Decimal("3000.01")))
    with pytest.raises(PayrollConfigurationError, match="cannot exceed"):
        PayrollService._uk_ssp_snapshot(
            employee=employee(), period=period(), statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(), calculation_date=date(2026, 8, 31),
        )


def test_invalid_ssp_input_has_employee_context(monkeypatch):
    configure(monkeypatch, entry())

    def fail(**kwargs):
        raise ValueError("Qualifying days sick cannot be negative.")

    with pytest.raises(PayrollConfigurationError, match="UK-007"):
        PayrollService._uk_ssp_snapshot(
            employee=employee(), period=period(),
            statutory_engine=SimpleNamespace(calculate_statutory_sick_pay=fail),
            statutory_config=SimpleNamespace(), calculation_date=date(2026, 8, 31),
        )


def test_prior_paid_days_are_forwarded(monkeypatch):
    configure(monkeypatch, entry())
    monkeypatch.setattr(
        PayrollService,
        "_uk_prior_ssp_paid_days",
        classmethod(lambda cls, employee_id, calculation_date: 12),
    )
    captured = {}

    def calculate(**kwargs):
        captured.update(kwargs)
        value = result()
        value.prior_paid_qualifying_days = 12
        return value

    PayrollService._uk_ssp_snapshot(
        employee=employee(), period=period(),
        statutory_engine=SimpleNamespace(calculate_statutory_sick_pay=calculate),
        statutory_config=SimpleNamespace(), calculation_date=date(2026, 8, 31),
    )
    assert captured["prior_paid_qualifying_days"] == 12


def test_prior_paid_days_sum_history(monkeypatch):
    rows = [
        SimpleNamespace(uk_ssp_payable_days=3),
        SimpleNamespace(uk_ssp_payable_days=None),
        SimpleNamespace(uk_ssp_payable_days=5),
    ]
    monkeypatch.setattr(
        PayrollService,
        "_uk_history_records",
        staticmethod(lambda employee_id, calculation_date: rows),
    )
    assert PayrollService._uk_prior_ssp_paid_days(7, date(2026, 8, 31)) == 8


def test_payslip_ssp_value_is_money_formatted():
    assert PayslipService._money(Decimal("73.95")) == "73.95"
