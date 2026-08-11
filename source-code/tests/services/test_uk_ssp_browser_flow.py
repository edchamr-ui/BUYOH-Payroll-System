"""Focused validation for the Draft-period UK SSP browser contract."""

from datetime import date
from types import SimpleNamespace

from flask import Flask

from app.payroll_periods.forms import PayrollSSPInputForm
from app.payroll_periods.routes import can_manage_ssp, validate_ssp_dates


def build_form(**overrides):
    data = {
        "sickness_start_date": "2026-06-10",
        "average_weekly_earnings": "500.00",
        "qualifying_days_per_week": "5",
        "qualifying_days_sick": "3",
        "salary_withheld": "147.90",
        "notes": "Three qualifying days in June.",
    }
    data.update(overrides)
    application = Flask(__name__)
    application.config.update(SECRET_KEY="test", WTF_CSRF_ENABLED=False)

    with application.test_request_context(method="POST", data=data):
        form = PayrollSSPInputForm()
        form.validate()
        return form


def period(status="Draft", is_open=True, end_date=date(2026, 6, 30)):
    return SimpleNamespace(
        status=status,
        end_date=end_date,
        payroll_year=SimpleNamespace(is_open=is_open),
    )


def test_supported_ssp_input_is_valid():
    form = build_form()
    assert not form.errors


def test_zero_awe_and_zero_sick_days_are_valid_inputs():
    form = build_form(
        average_weekly_earnings="0",
        qualifying_days_sick="0",
        salary_withheld="0",
    )
    assert not form.errors


def test_qualifying_days_per_week_must_be_between_one_and_seven():
    form = build_form(qualifying_days_per_week="8")
    assert form.qualifying_days_per_week.errors == [
        "Enter between 1 and 7 qualifying days."
    ]


def test_negative_salary_withheld_is_rejected():
    form = build_form(salary_withheld="-0.01")
    assert form.salary_withheld.errors == ["Salary withheld cannot be negative."]


def test_notes_are_limited_to_database_column_size():
    form = build_form(notes="x" * 501)
    assert form.notes.errors


def test_ssp_changes_require_an_open_draft_period():
    assert can_manage_ssp(period()) is True
    assert can_manage_ssp(period(status="Processed")) is False
    assert can_manage_ssp(period(is_open=False)) is False
    assert can_manage_ssp(SimpleNamespace(status="Draft", payroll_year=None)) is False


def test_sickness_start_cannot_be_after_period_end():
    form = build_form(sickness_start_date="2026-07-01")
    assert validate_ssp_dates(form, period()) == [
        "Sickness start date cannot be after the payroll period end date."
    ]


def test_sickness_may_start_before_current_period():
    form = build_form(sickness_start_date="2026-05-20")
    assert validate_ssp_dates(form, period()) == []
