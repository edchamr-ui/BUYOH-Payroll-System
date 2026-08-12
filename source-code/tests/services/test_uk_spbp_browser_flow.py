"""Browser-facing SPBP form and Draft-period validation tests."""

from datetime import date
from types import SimpleNamespace

from flask import Flask

from app.payroll_periods.forms import PayrollSPBPInputForm
from app.payroll_periods.routes import can_manage_spbp, validate_spbp_input


def build_form(**overrides):
    data = {
        "entitlement_reference": "BEREAVEMENT-2026-001",
        "bereavement_date": "2026-07-20",
        "bereavement_pay_period_start": "2026-08-03",
        "average_weekly_earnings": "500",
        "paid_days": "7",
        "salary_withheld": "700",
        "eligibility_confirmed": "y",
        "notice_received": "y",
        "declaration_received": "y",
        "notes": "Checked",
    }
    data.update(overrides)
    data = {key: value for key, value in data.items() if value is not None}
    app = Flask(__name__)
    app.config.update(SECRET_KEY="test", WTF_CSRF_ENABLED=False)
    with app.test_request_context(method="POST", data=data):
        form = PayrollSPBPInputForm()
        form.validate()
        return form


def period(status="Draft", open_year=True, end_date=date(2026, 8, 31)):
    return SimpleNamespace(
        status=status,
        end_date=end_date,
        payroll_year=SimpleNamespace(is_open=open_year),
    )


def test_valid_spbp_form():
    assert not build_form().errors


def test_reference_is_required():
    assert build_form(entitlement_reference="").entitlement_reference.errors


def test_paid_days_are_limited_to_entitlement():
    assert build_form(paid_days="15").paid_days.errors == [
        "Enter between 0 and 14 paid days."
    ]


def test_all_operational_evidence_is_required():
    assert build_form(eligibility_confirmed=None).eligibility_confirmed.errors
    assert build_form(notice_received=None).notice_received.errors
    assert build_form(declaration_received=None).declaration_received.errors


def test_spbp_inputs_obey_draft_period_locking():
    assert can_manage_spbp(period())
    assert not can_manage_spbp(period(status="Processed"))
    assert not can_manage_spbp(period(open_year=False))


def test_dates_cannot_be_after_period_end():
    form = build_form(
        bereavement_date="2026-09-01",
        bereavement_pay_period_start="2026-09-02",
    )
    errors = validate_spbp_input(form, period())
    assert "Bereavement date cannot be after" in errors[0]
    assert "pay period start cannot be after" in errors[1]


def test_leave_cannot_start_before_bereavement():
    errors = validate_spbp_input(
        build_form(bereavement_pay_period_start="2026-07-19"),
        period(),
    )
    assert errors == [
        "Parental bereavement leave cannot start before the bereavement date."
    ]


def test_leave_start_must_be_inside_56_week_window():
    errors = validate_spbp_input(
        build_form(bereavement_pay_period_start="2027-08-17"),
        period(end_date=date(2027, 8, 31)),
    )
    assert errors == [
        "Parental bereavement leave must start within 56 weeks of the "
        "bereavement date.",
        "Parental bereavement leave must finish within 56 weeks of the "
        "bereavement date.",
    ]


def test_leave_finish_must_be_inside_56_week_window():
    errors = validate_spbp_input(
        build_form(
            bereavement_pay_period_start="2027-08-16",
            paid_days="7",
        ),
        period(end_date=date(2027, 8, 31)),
    )
    assert errors == [
        "Parental bereavement leave must finish within 56 weeks of the "
        "bereavement date."
    ]


def test_notes_length_is_limited():
    assert build_form(notes="x" * 501).notes.errors
