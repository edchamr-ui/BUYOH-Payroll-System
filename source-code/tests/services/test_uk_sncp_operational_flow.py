"""Operational SNCP persistence, payroll and reporting tests."""

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
        id=7,
        employee_number="UK-007",
        basic_salary=Decimal("3000.00"),
    )


def period():
    return SimpleNamespace(id=11)


def entry(**overrides):
    values = {
        "entitlement_reference": "NEONATAL-2026-001",
        "baby_date_of_birth": date(2026, 7, 1),
        "neonatal_care_start_date": date(2026, 7, 3),
        "neonatal_care_through_date": date(2026, 7, 31),
        "neonatal_pay_period_start": date(2026, 7, 11),
        "average_weekly_earnings": Decimal("500.00"),
        "paid_days": 7,
        "salary_withheld": Decimal("700.00"),
        "eligibility_confirmed": True,
        "service_confirmed": True,
        "neonatal_care_confirmed": True,
        "notice_received": True,
        "declaration_received": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def result(**overrides):
    values = {
        "amount": Decimal("194.32"),
        "average_weekly_earnings": Decimal("500.00"),
        "weekly_rate": Decimal("194.32"),
        "accrued_weeks": 4,
        "accrued_days": 28,
        "payable_days": 7,
        "prior_paid_days": 0,
        "remaining_accrued_days": 21,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def configure(monkeypatch, sncp_entry):
    import app.services.payroll_service as payroll_service_module

    monkeypatch.setattr(
        payroll_service_module,
        "PayrollSNCPInput",
        SimpleNamespace(query=FakeQuery(sncp_entry)),
    )
    monkeypatch.setattr(
        PayrollService,
        "_uk_prior_sncp_paid_days",
        classmethod(lambda cls, *args: 0),
    )


def calculate(monkeypatch, sncp_entry=None, **result_overrides):
    configure(monkeypatch, sncp_entry)
    engine = SimpleNamespace(
        calculate_statutory_neonatal_care_pay=(
            lambda **kwargs: result(**result_overrides)
        )
    )
    return PayrollService._uk_sncp_snapshot(
        employee=employee(),
        period=period(),
        statutory_engine=engine,
        statutory_config=SimpleNamespace(),
        calculation_date=date(2026, 8, 31),
    )


def test_no_input_returns_no_pay_or_withholding(monkeypatch):
    amount, withheld, snapshot = calculate(monkeypatch)
    assert amount == Decimal("0.00")
    assert withheld == Decimal("0.00")
    assert snapshot == {}


def test_sncp_replaces_withheld_salary(monkeypatch):
    amount, withheld, snapshot = calculate(monkeypatch, entry())
    assert amount == Decimal("194.32")
    assert withheld == Decimal("700.00")
    assert snapshot["uk_sncp_remaining_accrued_days"] == 21


def test_snapshot_preserves_dates_and_derived_care_weeks(monkeypatch):
    _, _, snapshot = calculate(monkeypatch, entry())
    assert snapshot["uk_sncp_entitlement_reference"] == "NEONATAL-2026-001"
    assert snapshot["uk_sncp_accrued_weeks"] == 4
    assert snapshot["uk_sncp_baby_date_of_birth"] == date(2026, 7, 1)
    assert snapshot["uk_sncp_care_through_date"] == date(2026, 7, 31)


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("eligibility_confirmed", "eligibility"),
        ("service_confirmed", "service"),
        ("neonatal_care_confirmed", "care"),
        ("notice_received", "notice"),
        ("declaration_received", "declaration"),
    ),
)
def test_required_operational_evidence(monkeypatch, field, message):
    configure(monkeypatch, entry(**{field: False}))
    with pytest.raises(PayrollConfigurationError, match=message):
        PayrollService._uk_sncp_snapshot(
            employee=employee(), period=period(),
            statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"neonatal_care_start_date": date(2026, 6, 30)}, "before"),
        ({"neonatal_care_start_date": date(2026, 7, 30)}, "28 days"),
        ({"neonatal_care_through_date": date(2026, 7, 2)}, "before care"),
        ({"neonatal_care_through_date": date(2026, 7, 9)}, "7 consecutive"),
        ({"neonatal_pay_period_start": date(2026, 7, 10)}, "qualifying care week"),
        ({"neonatal_pay_period_start": date(2027, 10, 21)}, "start within 68 weeks"),
        ({"neonatal_pay_period_start": date(2027, 10, 20), "paid_days": 7}, "finish within 68 weeks"),
    ),
)
def test_statutory_date_rules(monkeypatch, overrides, message):
    configure(monkeypatch, entry(**overrides))
    with pytest.raises(PayrollConfigurationError, match=message):
        PayrollService._uk_sncp_snapshot(
            employee=employee(), period=period(),
            statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


def test_salary_withheld_cannot_exceed_contractual_salary(monkeypatch):
    configure(monkeypatch, entry(salary_withheld=Decimal("3000.01")))
    with pytest.raises(PayrollConfigurationError, match="cannot exceed"):
        PayrollService._uk_sncp_snapshot(
            employee=employee(), period=period(),
            statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


def test_invalid_sncp_input_has_employee_context(monkeypatch):
    configure(monkeypatch, entry())

    def fail(**kwargs):
        raise ValueError("Paid days cannot be negative.")

    with pytest.raises(PayrollConfigurationError, match="UK-007"):
        PayrollService._uk_sncp_snapshot(
            employee=employee(), period=period(),
            statutory_engine=SimpleNamespace(
                calculate_statutory_neonatal_care_pay=fail
            ),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


def test_accrued_and_prior_days_are_forwarded(monkeypatch):
    configure(monkeypatch, entry())
    monkeypatch.setattr(
        PayrollService,
        "_uk_prior_sncp_paid_days",
        classmethod(lambda cls, *args: 14),
    )
    captured = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return result(prior_paid_days=14, remaining_accrued_days=7)

    PayrollService._uk_sncp_snapshot(
        employee=employee(), period=period(),
        statutory_engine=SimpleNamespace(
            calculate_statutory_neonatal_care_pay=capture
        ),
        statutory_config=SimpleNamespace(),
        calculation_date=date(2026, 8, 31),
    )
    assert captured["accrued_weeks"] == 4
    assert captured["prior_paid_days"] == 14


def test_prior_paid_days_sum_entitlement_history(monkeypatch):
    rows = [
        SimpleNamespace(uk_sncp_paid_days=7),
        SimpleNamespace(uk_sncp_paid_days=None),
        SimpleNamespace(uk_sncp_paid_days=14),
    ]
    monkeypatch.setattr(
        PayrollService,
        "_uk_sncp_history_records",
        staticmethod(lambda *args: rows),
    )
    assert PayrollService._uk_prior_sncp_paid_days(
        7, "NEONATAL-2026-001", date(2026, 8, 31)
    ) == 21


def test_payslip_sncp_value_is_money_formatted():
    assert PayslipService._money(Decimal("1194.32")) == "1,194.32"
