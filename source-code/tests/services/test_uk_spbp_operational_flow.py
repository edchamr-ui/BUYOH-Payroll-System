"""Operational SPBP persistence, payroll and reporting tests."""

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
        "entitlement_reference": "BEREAVEMENT-2026-001",
        "bereavement_date": date(2026, 7, 20),
        "bereavement_pay_period_start": date(2026, 8, 3),
        "average_weekly_earnings": Decimal("500.00"),
        "paid_days": 7,
        "salary_withheld": Decimal("700.00"),
        "eligibility_confirmed": True,
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
        "payable_days": 7,
        "prior_paid_days": 0,
        "remaining_paid_days": 7,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def configure(monkeypatch, spbp_entry):
    import app.services.payroll_service as payroll_service_module

    monkeypatch.setattr(
        payroll_service_module,
        "PayrollSPBPInput",
        SimpleNamespace(query=FakeQuery(spbp_entry)),
    )
    monkeypatch.setattr(
        PayrollService,
        "_uk_prior_spbp_paid_days",
        classmethod(lambda cls, *args: 0),
    )


def calculate(monkeypatch, spbp_entry=None, **result_overrides):
    configure(monkeypatch, spbp_entry)
    engine = SimpleNamespace(
        calculate_statutory_parental_bereavement_pay=(
            lambda **kwargs: result(**result_overrides)
        )
    )
    return PayrollService._uk_spbp_snapshot(
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


def test_spbp_replaces_withheld_salary(monkeypatch):
    amount, withheld, snapshot = calculate(monkeypatch, entry())
    assert amount == Decimal("194.32")
    assert withheld == Decimal("700.00")
    assert snapshot["uk_spbp_amount"] == amount
    assert snapshot["uk_spbp_remaining_paid_days"] == 7


def test_snapshot_preserves_entitlement_and_dates(monkeypatch):
    _, _, snapshot = calculate(monkeypatch, entry())
    assert snapshot["uk_spbp_entitlement_reference"] == "BEREAVEMENT-2026-001"
    assert snapshot["uk_spbp_bereavement_date"] == date(2026, 7, 20)
    assert snapshot["uk_spbp_period_start_date"] == date(2026, 8, 3)


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("eligibility_confirmed", "eligibility"),
        ("notice_received", "notice"),
        ("declaration_received", "declaration"),
    ),
)
def test_required_operational_evidence(monkeypatch, field, message):
    configure(monkeypatch, entry(**{field: False}))
    with pytest.raises(PayrollConfigurationError, match=message):
        PayrollService._uk_spbp_snapshot(
            employee=employee(),
            period=period(),
            statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


@pytest.mark.parametrize(
    ("start_date", "message"),
    (
        (date(2026, 7, 19), "before"),
        (date(2027, 8, 17), "56 weeks"),
    ),
)
def test_leave_start_must_be_inside_statutory_window(
    monkeypatch, start_date, message
):
    configure(
        monkeypatch,
        entry(bereavement_pay_period_start=start_date),
    )
    with pytest.raises(PayrollConfigurationError, match=message):
        PayrollService._uk_spbp_snapshot(
            employee=employee(),
            period=period(),
            statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


def test_leave_must_finish_inside_statutory_window(monkeypatch):
    configure(
        monkeypatch,
        entry(
            bereavement_pay_period_start=date(2027, 8, 16),
            paid_days=7,
        ),
    )
    with pytest.raises(PayrollConfigurationError, match="finish within 56 weeks"):
        PayrollService._uk_spbp_snapshot(
            employee=employee(),
            period=period(),
            statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


def test_salary_withheld_cannot_exceed_contractual_salary(monkeypatch):
    configure(monkeypatch, entry(salary_withheld=Decimal("3000.01")))
    with pytest.raises(PayrollConfigurationError, match="cannot exceed"):
        PayrollService._uk_spbp_snapshot(
            employee=employee(),
            period=period(),
            statutory_engine=SimpleNamespace(),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


def test_invalid_spbp_input_has_employee_context(monkeypatch):
    configure(monkeypatch, entry())

    def fail(**kwargs):
        raise ValueError("Paid days cannot be negative.")

    with pytest.raises(PayrollConfigurationError, match="UK-007"):
        PayrollService._uk_spbp_snapshot(
            employee=employee(),
            period=period(),
            statutory_engine=SimpleNamespace(
                calculate_statutory_parental_bereavement_pay=fail
            ),
            statutory_config=SimpleNamespace(),
            calculation_date=date(2026, 8, 31),
        )


def test_prior_paid_days_are_forwarded(monkeypatch):
    configure(monkeypatch, entry())
    monkeypatch.setattr(
        PayrollService,
        "_uk_prior_spbp_paid_days",
        classmethod(lambda cls, *args: 7),
    )
    captured = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return result(prior_paid_days=7, remaining_paid_days=0)

    PayrollService._uk_spbp_snapshot(
        employee=employee(),
        period=period(),
        statutory_engine=SimpleNamespace(
            calculate_statutory_parental_bereavement_pay=capture
        ),
        statutory_config=SimpleNamespace(),
        calculation_date=date(2026, 8, 31),
    )
    assert captured["prior_paid_days"] == 7
    assert captured["payment_date"] == date(2026, 8, 31)


def test_prior_paid_days_sum_entitlement_history(monkeypatch):
    rows = [
        SimpleNamespace(uk_spbp_paid_days=7),
        SimpleNamespace(uk_spbp_paid_days=None),
        SimpleNamespace(uk_spbp_paid_days=4),
    ]
    monkeypatch.setattr(
        PayrollService,
        "_uk_spbp_history_records",
        staticmethod(lambda *args: rows),
    )
    assert PayrollService._uk_prior_spbp_paid_days(
        7, "BEREAVEMENT-2026-001", date(2026, 8, 31)
    ) == 11


def test_payslip_spbp_value_is_money_formatted():
    assert PayslipService._money(Decimal("1194.32")) == "1,194.32"
