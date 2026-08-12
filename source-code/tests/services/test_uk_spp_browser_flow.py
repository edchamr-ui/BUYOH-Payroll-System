"""Focused validation for the Draft-period UK SPP browser contract."""

from datetime import date
from types import SimpleNamespace

from flask import Flask

from app.payroll_periods.forms import PayrollSPPInputForm
from app.payroll_periods.routes import can_manage_spp, validate_spp_dates


def build_form(**overrides):
    data = {
        "paternity_pay_period_start": "2026-08-03",
        "average_weekly_earnings": "500.00",
        "paid_days": "7",
        "salary_withheld": "700.00",
        "eligibility_confirmed": "y",
        "declaration_received": "y",
        "notes": "Declaration retained.",
    }
    data.update(overrides)
    data = {key: value for key, value in data.items() if value is not None}
    application = Flask(__name__)
    application.config.update(SECRET_KEY="test", WTF_CSRF_ENABLED=False)
    with application.test_request_context(method="POST", data=data):
        form = PayrollSPPInputForm()
        form.validate()
        return form


def period(status="Draft", is_open=True, end_date=date(2026, 8, 31)):
    return SimpleNamespace(status=status, end_date=end_date, payroll_year=SimpleNamespace(is_open=is_open))


def test_supported_spp_input_is_valid():
    assert not build_form().errors


def test_zero_awe_days_and_withholding_are_valid():
    assert not build_form(average_weekly_earnings="0", paid_days="0", salary_withheld="0").errors


def test_paid_days_cannot_exceed_two_weeks():
    assert build_form(paid_days="15").paid_days.errors == ["Enter between 0 and 14 paid days."]


def test_negative_salary_withheld_is_rejected():
    assert build_form(salary_withheld="-0.01").salary_withheld.errors == ["Salary withheld cannot be negative."]


def test_eligibility_confirmation_is_required():
    assert build_form(eligibility_confirmed=None).eligibility_confirmed.errors == ["Confirm eligibility before saving SPP."]


def test_declaration_is_required():
    assert build_form(declaration_received=None).declaration_received.errors == ["Confirm the declaration before saving SPP."]


def test_notes_match_database_limit():
    assert build_form(notes="x" * 501).notes.errors


def test_spp_changes_require_open_draft_period():
    assert can_manage_spp(period()) is True
    assert can_manage_spp(period(status="Processed")) is False
    assert can_manage_spp(period(is_open=False)) is False


def test_paternity_start_cannot_be_after_period_end():
    form = build_form(paternity_pay_period_start="2026-09-01")
    assert validate_spp_dates(form, period()) == ["Paternity pay period start cannot be after the payroll period end date."]


def test_paternity_start_may_precede_current_period():
    assert validate_spp_dates(build_form(), period()) == []
