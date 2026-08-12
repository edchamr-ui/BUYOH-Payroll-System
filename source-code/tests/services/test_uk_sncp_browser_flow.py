"""Browser-facing SNCP form and Draft-period validation tests."""

from datetime import date
from types import SimpleNamespace

from flask import Flask

from app.payroll_periods.forms import PayrollSNCPInputForm
from app.payroll_periods.routes import can_manage_sncp, validate_sncp_input


def build_form(**overrides):
    data = {
        "entitlement_reference": "NEONATAL-2026-001",
        "baby_date_of_birth": "2026-07-01",
        "neonatal_care_start_date": "2026-07-02",
        "neonatal_care_through_date": "2026-07-09",
        "neonatal_pay_period_start": "2026-07-10",
        "average_weekly_earnings": "500",
        "paid_days": "7",
        "salary_withheld": "700",
        "eligibility_confirmed": "y",
        "service_confirmed": "y",
        "neonatal_care_confirmed": "y",
        "notice_received": "y",
        "declaration_received": "y",
        "notes": "Checked",
    }
    data.update(overrides)
    data = {key: value for key, value in data.items() if value is not None}
    app = Flask(__name__)
    app.config.update(SECRET_KEY="test", WTF_CSRF_ENABLED=False)
    with app.test_request_context(method="POST", data=data):
        form = PayrollSNCPInputForm()
        form.validate()
        return form


def period(status="Draft", open_year=True, end_date=date(2026, 7, 31)):
    return SimpleNamespace(
        status=status,
        end_date=end_date,
        payroll_year=SimpleNamespace(is_open=open_year),
    )


def test_valid_sncp_form():
    assert not build_form().errors


def test_reference_is_required():
    assert build_form(entitlement_reference="").entitlement_reference.errors


def test_paid_days_fit_the_payroll_period():
    assert build_form(paid_days="32").paid_days.errors == [
        "Enter between 0 and 31 paid days."
    ]


def test_all_operational_evidence_is_required():
    fields = (
        "eligibility_confirmed",
        "service_confirmed",
        "neonatal_care_confirmed",
        "notice_received",
        "declaration_received",
    )
    for field in fields:
        assert getattr(build_form(**{field: None}), field).errors


def test_sncp_inputs_obey_draft_period_locking():
    assert can_manage_sncp(period())
    assert not can_manage_sncp(period(status="Processed"))
    assert not can_manage_sncp(period(open_year=False))


def test_dates_cannot_be_after_period_end():
    form = build_form(
        baby_date_of_birth="2026-08-01",
        neonatal_care_start_date="2026-08-02",
        neonatal_care_through_date="2026-08-09",
        neonatal_pay_period_start="2026-08-10",
    )
    errors = validate_sncp_input(form, period())
    assert len(errors) == 4
    assert all("payroll period end date" in error for error in errors)


def test_care_cannot_start_before_birth():
    errors = validate_sncp_input(
        build_form(
            neonatal_care_start_date="2026-06-30",
            neonatal_care_through_date="2026-07-07",
            neonatal_pay_period_start="2026-07-08",
        ),
        period(),
    )
    assert errors == ["Neonatal care cannot start before the baby's birth."]


def test_care_must_start_inside_28_day_window():
    errors = validate_sncp_input(
        build_form(
            neonatal_care_start_date="2026-07-30",
            neonatal_care_through_date="2026-08-06",
            neonatal_pay_period_start="2026-08-07",
        ),
        period(end_date=date(2026, 8, 31)),
    )
    assert errors == [
        "Neonatal care must start within 28 days of the baby's birth."
    ]


def test_care_through_cannot_precede_care_start():
    errors = validate_sncp_input(
        build_form(neonatal_care_through_date="2026-07-01"),
        period(),
    )
    assert errors == [
        "The neonatal care confirmed-through date cannot be before the "
        "care start date.",
        "At least 7 consecutive full days of neonatal care must be confirmed.",
    ]


def test_at_least_one_full_care_week_is_required():
    errors = validate_sncp_input(
        build_form(neonatal_care_through_date="2026-07-08"),
        period(),
    )
    assert errors == [
        "At least 7 consecutive full days of neonatal care must be confirmed."
    ]


def test_leave_waits_until_first_qualifying_week_is_complete():
    errors = validate_sncp_input(
        build_form(neonatal_pay_period_start="2026-07-09"),
        period(),
    )
    assert errors == [
        "Neonatal care leave cannot start before the first qualifying care "
        "week is complete."
    ]


def test_leave_start_must_be_inside_68_week_window():
    errors = validate_sncp_input(
        build_form(neonatal_pay_period_start="2027-10-21", paid_days="0"),
        period(end_date=date(2027, 10, 31)),
    )
    assert errors == [
        "Neonatal care leave must start within 68 weeks of the baby's birth."
    ]


def test_leave_finish_must_be_inside_68_week_window():
    errors = validate_sncp_input(
        build_form(neonatal_pay_period_start="2027-10-20", paid_days="7"),
        period(end_date=date(2027, 10, 31)),
    )
    assert errors == [
        "Neonatal care leave must finish within 68 weeks of the baby's birth."
    ]


def test_notes_length_is_limited():
    assert build_form(notes="x" * 501).notes.errors
