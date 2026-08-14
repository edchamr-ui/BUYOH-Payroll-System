"""Browser and Draft-period tests for transaction inputs."""

from datetime import date
from decimal import Decimal
from inspect import getsource
from pathlib import Path
from types import SimpleNamespace

from flask import Flask

from app.models.payroll_overtime_input import PayrollOvertimeInput
from app.payroll_periods.forms import (
    PayrollOneOffDeductionForm,
    PayrollOvertimeInputForm,
)
from app.payroll_periods.routes import (
    approve_one_off_deduction,
    approve_overtime_input,
    can_manage_transaction_inputs,
    delete_one_off_deduction,
    delete_overtime_input,
    edit_one_off_deduction,
    edit_overtime_input,
    validate_overtime_work_date,
)


def build_form(form_class, data):
    app = Flask(__name__)
    app.config.update(SECRET_KEY="test", WTF_CSRF_ENABLED=False)
    with app.test_request_context(method="POST", data=data):
        form = form_class()
        form.validate()
        return form


def overtime_form(**overrides):
    values = {
        "category": "Ordinary",
        "work_date": "2026-01-15",
        "hours": "10",
        "hourly_rate": "3.375",
        "multiplier": "1.5",
        "description": "Approved timesheet OT-001",
    }
    values.update(overrides)
    return build_form(PayrollOvertimeInputForm, values)


def deduction_form(**overrides):
    values = {
        "deduction_type": "Salary Advance Recovery",
        "amount": "30.00",
        "priority": "100",
        "description": "Advance ADV-001",
    }
    values.update(overrides)
    return build_form(PayrollOneOffDeductionForm, values)


def period(status="Draft", open_year=True):
    return SimpleNamespace(
        status=status,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        payroll_year=SimpleNamespace(is_open=open_year),
    )


def test_valid_overtime_form_and_server_calculation():
    form = overtime_form()
    assert not form.errors
    assert PayrollOvertimeInput.calculate_amount(
        form.hours.data,
        form.hourly_rate.data,
        form.multiplier.data,
    ) == Decimal("50.63")


def test_overtime_requires_positive_hours():
    assert overtime_form(hours="0").hours.errors == [
        "Enter overtime hours between 0.01 and 744."
    ]


def test_overtime_requires_positive_multiplier():
    assert overtime_form(multiplier="0").multiplier.errors == [
        "Enter a multiplier greater than zero and not above 10."
    ]


def test_overtime_work_date_must_be_inside_period():
    form = overtime_form(work_date="2026-02-01")
    assert validate_overtime_work_date(form, period()) == [
        "Overtime work date must fall inside the payroll period."
    ]


def test_valid_one_off_deduction_form():
    assert not deduction_form().errors


def test_one_off_deduction_must_be_positive():
    assert deduction_form(amount="0").amount.errors == [
        "The deduction must be greater than zero."
    ]


def test_recovery_priority_is_bounded():
    assert deduction_form(priority="1000").priority.errors == [
        "Enter a priority between 0 and 999."
    ]


def test_transaction_inputs_obey_draft_period_locking():
    assert can_manage_transaction_inputs(period())
    assert not can_manage_transaction_inputs(period(status="Processed"))
    assert not can_manage_transaction_inputs(period(open_year=False))


def test_approval_routes_use_csrf_locking_and_approval_metadata():
    overtime_source = getsource(approve_overtime_input)
    deduction_source = getsource(approve_one_off_deduction)
    for source in (overtime_source, deduction_source):
        assert "PayrollPeriodActionForm" in source
        assert "can_manage_transaction_inputs" in source
        assert 'status = "Approved"' in source
        assert "approved_by = current_user.id" in source
        assert "approved_at = legacy_utc_now()" in source


def test_editing_approved_inputs_returns_them_to_draft():
    for source in (
        getsource(edit_overtime_input),
        getsource(edit_one_off_deduction),
    ):
        assert 'status = "Draft"' in source
        assert "approved_by = None" in source
        assert "approved_at = None" in source


def test_only_draft_inputs_can_be_deleted():
    for source in (
        getsource(delete_overtime_input),
        getsource(delete_one_off_deduction),
    ):
        assert 'status != "Draft"' in source
        assert "validate_on_submit" in source


def test_period_view_links_to_transaction_workspace():
    template = Path(
        "app/templates/payroll_periods/view.html"
    ).read_text(encoding="utf-8")
    assert "list_transaction_inputs" in template
    assert "Overtime &amp; Deductions" in template
