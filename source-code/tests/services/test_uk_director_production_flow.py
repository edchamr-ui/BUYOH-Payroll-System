"""Production-facing validation for UK director employee settings."""

from datetime import date
from types import SimpleNamespace

from flask import Flask

import app.employees.routes as employee_routes
from app.employees.forms import EmployeeForm
from app.services.payslip_service import PayslipService


def build_form(**overrides):
    data = {
        "employee_number": "UK-001",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "national_id": "",
        "job_title": "Director",
        "department_id": "1",
        "employment_date": "2026-04-06",
        "termination_date": "",
        "basic_salary": "5000.00",
        "tax_residency": "Resident",
        "employment_status": "Active",
        "payment_method": "Cash",
        "bank_name": "",
        "bank_branch": "",
        "bank_code": "",
        "account_name": "",
        "account_number": "",
        "account_type": "",
        "uk_profile_enabled": "y",
        "uk_tax_code": "1257l",
        "uk_tax_basis": "CUMULATIVE",
        "uk_tax_region": "ENGLAND_NI",
        "uk_ni_category": "A",
        "is_director": "y",
        "director_ni_method": "ALTERNATIVE",
    }
    data.update(overrides)

    # An optional WTForms DateField must be omitted when it has no value.
    # Submitting an empty string causes "Not a valid date value."
    if data.get("termination_date") == "":
        data.pop("termination_date")

    application = Flask(__name__)
    application.config.update(
        SECRET_KEY="test",
        WTF_CSRF_ENABLED=False,
    )

    with application.test_request_context(method="POST", data=data):
        form = EmployeeForm()
        form.department_id.choices = [(1, "Finance")]
        form.validate()
        return form


def blank_employee(profile=None):
    return SimpleNamespace(
        employee_number=None,
        first_name=None,
        last_name=None,
        email=None,
        national_id=None,
        job_title=None,
        department_id=None,
        employment_date=None,
        termination_date=None,
        basic_salary=None,
        tax_residency=None,
        employment_status=None,
        is_active=None,
        payment_method=None,
        bank_name=None,
        bank_branch=None,
        bank_code=None,
        account_name=None,
        account_number=None,
        account_type=None,
        uk_tax_profile=profile,
    )


def profile(**overrides):
    values = {
        "tax_code": "1257L",
        "tax_basis": "CUMULATIVE",
        "tax_region": "ENGLAND_NI",
        "ni_category": "A",
        "is_director": True,
        "director_ni_method": "ALTERNATIVE",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_uk_director_form_accepts_supported_settings():
    form = build_form()

    assert not form.errors
    assert form.uk_tax_code.data == "1257L"
    assert form.uk_ni_category.data == "A"
    assert form.director_ni_method.data == "ALTERNATIVE"


def test_uk_profile_requires_tax_code():
    form = build_form(uk_tax_code="")

    assert form.uk_tax_code.errors == [
        "UK tax code is required when UK payroll is enabled.",
    ]


def test_non_uk_employee_does_not_require_tax_code():
    form = build_form(uk_profile_enabled="", uk_tax_code="")

    assert not form.uk_tax_code.errors


def test_terminated_employee_requires_termination_date():
    form = build_form(employment_status="Terminated")

    assert form.termination_date.errors == [
        "Termination date is required for a terminated employee.",
    ]


def test_termination_date_cannot_precede_employment():
    form = build_form(
        employment_status="Terminated",
        termination_date="2026-04-05",
    )

    assert form.termination_date.errors == [
        "Termination date cannot be before employment date.",
    ]


def test_terminated_director_accepts_coherent_final_date():
    form = build_form(
        employment_status="Terminated",
        termination_date="2026-09-30",
    )

    assert not form.errors
    assert form.termination_date.data == date(2026, 9, 30)


def test_apply_employee_form_creates_and_normalises_profile(monkeypatch):
    form = build_form()
    employee = blank_employee()

    monkeypatch.setattr(
        employee_routes,
        "EmployeeUKTaxProfile",
        SimpleNamespace,
    )

    employee_routes.apply_employee_form(employee, form)

    assert employee.uk_tax_profile.tax_code == "1257L"
    assert employee.uk_tax_profile.ni_category == "A"
    assert employee.uk_tax_profile.is_director is True
    assert employee.uk_tax_profile.director_ni_method == "ALTERNATIVE"


def test_apply_employee_form_persists_termination_date(monkeypatch):
    form = build_form(
        employment_status="Terminated",
        termination_date="2026-09-30",
    )
    employee = blank_employee()

    monkeypatch.setattr(
        employee_routes,
        "EmployeeUKTaxProfile",
        SimpleNamespace,
    )

    employee_routes.apply_employee_form(employee, form)

    assert employee.termination_date == date(2026, 9, 30)
    assert employee.is_active is False


def test_non_director_is_forced_to_standard_ni_method():
    form = build_form(is_director="")
    employee = blank_employee(profile())

    employee_routes.apply_employee_form(employee, form)

    assert employee.uk_tax_profile.is_director is False
    assert employee.uk_tax_profile.director_ni_method == "STANDARD"


def test_disabling_uk_payroll_removes_profile():
    form = build_form(uk_profile_enabled="")
    existing = profile()
    employee = blank_employee(existing)

    employee_routes.apply_employee_form(employee, form)

    assert employee.uk_tax_profile is None


def test_edit_form_populates_nested_uk_profile():
    form = build_form(uk_profile_enabled="")
    employee = blank_employee(
        profile(
            tax_code="S1257L",
            tax_region="SCOTLAND",
            ni_category="J",
        )
    )

    employee_routes.populate_uk_profile_form(form, employee)

    assert form.uk_profile_enabled.data is True
    assert form.uk_tax_code.data == "S1257L"
    assert form.uk_tax_region.data == "SCOTLAND"
    assert form.uk_ni_category.data == "J"
    assert form.is_director.data is True


def test_edit_form_leaves_non_uk_employee_disabled():
    form = build_form(uk_profile_enabled="")

    employee_routes.populate_uk_profile_form(form, blank_employee())

    assert form.uk_profile_enabled.data is False


def test_uk_payslip_uses_national_insurance_labels():
    record = SimpleNamespace(uk_tax_code="1257L")

    assert PayslipService._employee_social_security_label(record) == (
        "National Insurance (NI)"
    )
    assert PayslipService._employer_social_security_label(record) == (
        "Employer National Insurance"
    )


def test_non_uk_payslip_preserves_existing_nssa_labels():
    record = SimpleNamespace(uk_tax_code=None)

    assert PayslipService._employee_social_security_label(record) == (
        "NSSA Deduction"
    )
    assert PayslipService._employer_social_security_label(record) == (
        "Employer NSSA"
    )
