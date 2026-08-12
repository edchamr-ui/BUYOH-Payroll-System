"""Operational SPP persistence, payroll and reporting tests."""

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


def employee():
    return SimpleNamespace(
        id=7, employee_number="UK-007", basic_salary=Decimal("3000.00")
    )


def period():
    return SimpleNamespace(id=11)


def entry(**overrides):
    values = {
        "paternity_pay_period_start": date(2026, 8, 3),
        "average_weekly_earnings": Decimal("500.00"),
        "paid_days": 7,
        "salary_withheld": Decimal("700.00"),
        "eligibility_confirmed": True,
        "declaration_received": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def result(**overrides):
    values = {
        "amount": Decimal("194.32"),
        "average_weekly_earnings": Decimal("500.00"),
        "weekly_rate": Decimal("194.32"),
        "payable_days": 7,
        "prior_paid_days": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def configure(monkeypatch, spp_entry):
    import app.services.payroll_service as payroll_service_module

    monkeypatch.setattr(
        payroll_service_module,
        "PayrollSPPInput",
        SimpleNamespace(query=FakeQuery(spp_entry)),
    )
    monkeypatch.setattr(
        PayrollService,
        "_uk_prior_spp_paid_days",
        classmethod(
            lambda cls, employee_id, paternity_pay_period_start,
            calculation_date: 0
        ),
    )


def calculate(monkeypatch, spp_entry=None, **result_overrides):
    configure(monkeypatch, spp_entry)
    engine = SimpleNamespace(
        calculate_statutory_paternity_pay=lambda **kwargs: result(**result_overrides)
    )
    return PayrollService._uk_spp_snapshot(
        employee=employee(),
        period=period(),
        statutory_engine=engine,
        statutory_config=SimpleNamespace(),
        calculation_date=date(2026, 8, 31),
    )


def test_no_input_returns_no_pay_or_withholding(monkeypatch):
    amount, withheld, snapshot = calculate(monkeypatch, None)
    assert amount == Decimal("0.00")
    assert withheld == Decimal("0.00")
    assert snapshot == {}


def test_spp_replaces_withheld_salary(monkeypatch):
    amount, withheld, snapshot = calculate(monkeypatch, entry())
    assert amount == Decimal("194.32")
    assert withheld == Decimal("700.00")
    assert snapshot["uk_spp_amount"] == amount
    assert snapshot["uk_spp_salary_withheld"] == withheld


def test_snapshot_preserves_rate_days_and_evidence(monkeypatch):
    _, _, snapshot = calculate(monkeypatch, entry())
    assert snapshot["uk_spp_weekly_rate"] == Decimal("194.32")
    assert snapshot["uk_spp_paid_days"] == 7
    assert snapshot["uk_spp_eligibility_confirmed"] is True
    assert snapshot["uk_spp_declaration_received"] is True


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"eligibility_confirmed": False}, "eligibility"),
        ({"declaration_received": False}, "declaration"),
    ],
)
def test_required_operational_evidence(monkeypatch, overrides, message):
    configure(monkeypatch, entry(**overrides))
    with pytest.raises(PayrollConfigurationError, match=message):
        PayrollService._uk_spp_snapshot(
            employee=employee(), period=period(), statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(), calculation_date=date(2026, 8, 31),
        )


def test_salary_withheld_cannot_exceed_contractual_salary(monkeypatch):
    configure(monkeypatch, entry(salary_withheld=Decimal("3000.01")))
    with pytest.raises(PayrollConfigurationError, match="cannot exceed"):
        PayrollService._uk_spp_snapshot(
            employee=employee(), period=period(), statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(), calculation_date=date(2026, 8, 31),
        )


def test_invalid_spp_input_has_employee_context(monkeypatch):
    configure(monkeypatch, entry())

    def fail(**kwargs):
        raise ValueError("Paid days cannot be negative.")

    with pytest.raises(PayrollConfigurationError, match="UK-007"):
        PayrollService._uk_spp_snapshot(
            employee=employee(), period=period(),
            statutory_engine=SimpleNamespace(calculate_statutory_paternity_pay=fail),
            statutory_config=SimpleNamespace(), calculation_date=date(2026, 8, 31),
        )


def test_prior_paid_days_are_forwarded(monkeypatch):
    configure(monkeypatch, entry())
    monkeypatch.setattr(
        PayrollService,
        "_uk_prior_spp_paid_days",
        classmethod(
            lambda cls, employee_id, paternity_pay_period_start,
            calculation_date: 7
        ),
    )
    captured = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return result(prior_paid_days=7)

    PayrollService._uk_spp_snapshot(
        employee=employee(), period=period(),
        statutory_engine=SimpleNamespace(calculate_statutory_paternity_pay=capture),
        statutory_config=SimpleNamespace(), calculation_date=date(2026, 8, 31),
    )
    assert captured["prior_paid_days"] == 7
    assert captured["payment_date"] == date(2026, 8, 31)


def test_prior_paid_days_sum_history(monkeypatch):
    rows = [
        SimpleNamespace(uk_spp_paid_days=7),
        SimpleNamespace(uk_spp_paid_days=None),
        SimpleNamespace(uk_spp_paid_days=4),
    ]
    monkeypatch.setattr(
        PayrollService,
        "_uk_spp_history_records",
        staticmethod(
            lambda employee_id, paternity_pay_period_start,
            calculation_date: rows
        ),
    )
    assert PayrollService._uk_prior_spp_paid_days(
        7, date(2026, 8, 3), date(2026, 8, 31)
    ) == 11


def test_payslip_spp_value_is_money_formatted():
    assert PayslipService._money(Decimal("1194.32")) == "1,194.32"
