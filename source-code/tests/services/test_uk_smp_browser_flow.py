"""Focused validation for the Draft-period UK SMP browser contract."""

from datetime import date
from types import SimpleNamespace

from flask import Flask

from app.payroll_periods.forms import PayrollSMPInputForm
from app.payroll_periods.routes import can_manage_smp, validate_smp_dates


def build_form(**overrides):
    data = {
        "maternity_pay_period_start": "2026-05-03",
        "average_weekly_earnings": "650.00",
        "paid_days": "30",
        "salary_withheld": "1992.86",
        "eligibility_confirmed": "y",
        "matb1_received": "y",
        "notes": "MATB1 checked and retained.",
    }
    data.update(overrides)
    data = {key: value for key, value in data.items() if value is not None}
    application = Flask(__name__)
    application.config.update(SECRET_KEY="test", WTF_CSRF_ENABLED=False)

    with application.test_request_context(method="POST", data=data):
        form = PayrollSMPInputForm()
        form.validate()
        return form


def period(status="Draft", is_open=True, end_date=date(2026, 6, 30)):
    return SimpleNamespace(
        status=status,
        end_date=end_date,
        payroll_year=SimpleNamespace(is_open=is_open),
    )


def test_supported_smp_input_is_valid():
    assert not build_form().errors


def test_zero_awe_paid_days_and_salary_withheld_are_valid():
    form = build_form(
        average_weekly_earnings="0",
        paid_days="0",
        salary_withheld="0",
    )
    assert not form.errors


def test_paid_days_must_fit_within_a_month():
    form = build_form(paid_days="32")
    assert form.paid_days.errors == ["Enter between 0 and 31 paid days."]


def test_negative_salary_withheld_is_rejected():
    form = build_form(salary_withheld="-0.01")
    assert form.salary_withheld.errors == ["Salary withheld cannot be negative."]


def test_eligibility_confirmation_is_required():
    form = build_form(eligibility_confirmed=None)
    assert form.eligibility_confirmed.errors == [
        "Confirm eligibility before saving SMP."
    ]


def test_matb1_evidence_is_required():
    form = build_form(matb1_received=None)
    assert form.matb1_received.errors == [
        "Confirm MATB1 evidence before saving SMP."
    ]


def test_notes_are_limited_to_database_column_size():
    assert build_form(notes="x" * 501).notes.errors


def test_smp_changes_require_an_open_draft_period():
    assert can_manage_smp(period()) is True
    assert can_manage_smp(period(status="Processed")) is False
    assert can_manage_smp(period(is_open=False)) is False
    assert can_manage_smp(SimpleNamespace(status="Draft", payroll_year=None)) is False


def test_maternity_pay_period_cannot_start_after_period_end():
    form = build_form(maternity_pay_period_start="2026-07-01")
    assert validate_smp_dates(form, period()) == [
        "Maternity pay period start cannot be after the payroll period end date."
    ]


def test_maternity_pay_period_may_start_before_current_period():
    form = build_form(maternity_pay_period_start="2026-05-03")
    assert validate_smp_dates(form, period()) == []
