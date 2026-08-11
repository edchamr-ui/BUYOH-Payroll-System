from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.orm import joinedload, selectinload
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.employees import employees_bp
from app.employees.forms import EmployeeForm
from app.extensions import db
from app.models import (
    Department,
    EmailDelivery,
    Employee,
    EmployeeUKTaxProfile,
    PayrollRecord,
)

def load_department_choices(form):
    """Populate the department dropdown from active departments."""

    departments = (
        Department.query
        .filter_by(is_active=True)
        .order_by(Department.name.asc())
        .all()
    )

    form.department_id.choices = [
        (department.id, department.name)
        for department in departments
    ]


def clean_optional_text(value):
    """Strip optional text and convert blank values to None."""

    if value is None:
        return None

    cleaned_value = value.strip()

    return cleaned_value or None


def apply_employee_form(employee, form):
    """Apply validated employee form data to the model."""

    employee.employee_number = (
        form.employee_number.data.strip()
    )

    employee.first_name = (
        form.first_name.data.strip()
    )

    employee.last_name = (
        form.last_name.data.strip()
    )

    employee.email = clean_optional_text(
        form.email.data
    )

    if employee.email:
        employee.email = employee.email.lower()
    employee.national_id = clean_optional_text(
        form.national_id.data
    )

    employee.job_title = (
        form.job_title.data.strip()
    )

    employee.department_id = (
        form.department_id.data
    )

    employee.employment_date = (
        form.employment_date.data
    )

    employee.termination_date = (
        form.termination_date.data
    )

    employee.basic_salary = (
        form.basic_salary.data
    )

    employee.tax_residency = (
        form.tax_residency.data
    )

    employee.employment_status = (
        form.employment_status.data
    )

    employee.is_active = (
        form.employment_status.data != "Terminated"
    )

    employee.payment_method = (
        form.payment_method.data
    )

    employee.bank_name = clean_optional_text(
        form.bank_name.data
    )

    employee.bank_branch = clean_optional_text(
        form.bank_branch.data
    )

    employee.bank_code = clean_optional_text(
        form.bank_code.data
    )

    employee.account_name = clean_optional_text(
        form.account_name.data
    )

    employee.account_number = clean_optional_text(
        form.account_number.data
    )

    employee.account_type = clean_optional_text(
        form.account_type.data
    )

    if form.uk_profile_enabled.data:
        profile = employee.uk_tax_profile
        if profile is None:
            profile = EmployeeUKTaxProfile()
            employee.uk_tax_profile = profile

        profile.tax_code = form.uk_tax_code.data.strip().upper()
        profile.tax_basis = form.uk_tax_basis.data
        profile.tax_region = form.uk_tax_region.data
        profile.ni_category = form.uk_ni_category.data
        profile.is_director = bool(form.is_director.data)
        profile.director_ni_method = (
            form.director_ni_method.data
            if profile.is_director
            else "STANDARD"
        )
    elif employee.uk_tax_profile is not None:
        employee.uk_tax_profile = None


def populate_uk_profile_form(form, employee):
    """Populate nested UK profile fields when editing an employee."""

    profile = employee.uk_tax_profile
    if profile is None:
        return

    form.uk_profile_enabled.data = True
    form.uk_tax_code.data = profile.tax_code
    form.uk_tax_basis.data = profile.tax_basis
    form.uk_tax_region.data = profile.tax_region
    form.uk_ni_category.data = profile.ni_category
    form.is_director.data = profile.is_director
    form.director_ni_method.data = profile.director_ni_method


@employees_bp.route("/")
@login_required
def list_employees():
    """Display searchable, filtered and paginated employees."""

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    department_id = request.args.get(
        "department_id",
        type=int,
    )

    status_filter = request.args.get(
        "status",
        "all",
    ).strip().lower()

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    per_page = 20

    query = (
        Employee.query
        .outerjoin(Department)
    )

    if search_term:
        search_pattern = f"%{search_term}%"

        query = query.filter(
            or_(
                Employee.employee_number.ilike(
                    search_pattern
                ),
                Employee.first_name.ilike(
                    search_pattern
                ),
                Employee.last_name.ilike(
                    search_pattern
                ),
                Employee.email.ilike(
                    search_pattern
                ),
                Employee.national_id.ilike(
                    search_pattern
                ),
                Employee.job_title.ilike(
                    search_pattern
                ),
                Employee.payment_method.ilike(
                    search_pattern
                ),
                Employee.bank_name.ilike(
                    search_pattern
                ),
                Employee.account_name.ilike(
                    search_pattern
                ),
                Employee.account_number.ilike(
                    search_pattern
                ),
                Department.name.ilike(
                    search_pattern
                ),
            )
        )

    if department_id:
        query = query.filter(
            Employee.department_id == department_id
        )

    if status_filter == "active":
        query = query.filter(
            Employee.is_active.is_(True)
        )

    elif status_filter == "inactive":
        query = query.filter(
            Employee.is_active.is_(False)
        )

    pagination = (
        query
        .order_by(
            Employee.first_name.asc(),
            Employee.last_name.asc(),
        )
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )
    )

    departments = (
        Department.query
        .order_by(Department.name.asc())
        .all()
    )

    return render_template(
        "employees/list.html",
        employees=pagination.items,
        pagination=pagination,
        departments=departments,
        search_term=search_term,
        selected_department_id=department_id,
        status_filter=status_filter,
    )

@employees_bp.route(
    "/add",
    methods=["GET", "POST"],
)
@login_required
def add_employee():
    """Create a new employee."""

    form = EmployeeForm()

    load_department_choices(form)

    if form.validate_on_submit():
        employee = Employee()

        apply_employee_form(
            employee,
            form,
        )

        db.session.add(employee)

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "Employee number or national ID, or email "
                    "already exists."
                ),
                "danger",
            )

            return render_template(
                "employees/form.html",
                form=form,
                page_heading="Add Employee",
            )

        flash(
            "Employee added successfully.",
            "success",
        )

        return redirect(
            url_for("employees.list_employees")
        )

    return render_template(
        "employees/form.html",
        form=form,
        page_heading="Add Employee",
    )


@employees_bp.route("/<int:employee_id>")
@login_required
def view_employee(employee_id):
    """Display the employee workspace and payroll history."""

    employee = (
        Employee.query
        .options(
            joinedload(Employee.department),
            selectinload(Employee.payroll_records)
            .joinedload(PayrollRecord.payroll_period),
            selectinload(Employee.payroll_records)
            .joinedload(PayrollRecord.payslip),
            selectinload(Employee.allowances),
            selectinload(Employee.deductions),
            selectinload(Employee.payslips),
        )
        .filter(Employee.id == employee_id)
        .first_or_404()
    )

    payroll_records = sorted(
        employee.payroll_records,
        key=lambda record: (
            record.payroll_period.year,
            record.payroll_period.month,
            record.id,
        ),
        reverse=True,
    )

    latest_payroll_record = (
        payroll_records[0]
        if payroll_records
        else None
    )

    latest_allowances = []
    latest_deductions = []

    if latest_payroll_record:
        latest_allowances = sorted(
            latest_payroll_record.allowances,
            key=lambda allowance: allowance.amount,
            reverse=True,
        )

        latest_deductions = sorted(
            latest_payroll_record.deductions,
            key=lambda deduction: deduction.amount,
            reverse=True,
        )

    email_deliveries = (
        employee.email_deliveries
        .order_by(
            EmailDelivery.created_at.desc(),
            EmailDelivery.id.desc(),
        )
        .limit(10)
        .all()
    )

    total_payroll_periods = len(payroll_records)

    generated_payslip_count = sum(
        1
        for record in payroll_records
        if record.payslip is not None
    )

    return render_template(
        "employees/view.html",
        employee=employee,
        payroll_records=payroll_records,
        latest_payroll_record=latest_payroll_record,
        latest_allowances=latest_allowances,
        latest_deductions=latest_deductions,
        email_deliveries=email_deliveries,
        total_payroll_periods=total_payroll_periods,
        generated_payslip_count=generated_payslip_count,
    )

@employees_bp.route(
    "/<int:employee_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_employee(employee_id):
    """Update an existing employee record."""

    employee = Employee.query.get_or_404(
        employee_id
    )

    form = EmployeeForm(obj=employee)

    load_department_choices(form)

    if request.method == "GET":
        populate_uk_profile_form(form, employee)

    if form.validate_on_submit():
        apply_employee_form(
            employee,
            form,
        )

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "Employee number or national ID "
                    "already exists."
                ),
                "danger",
            )

            return render_template(
                "employees/form.html",
                form=form,
                page_heading="Edit Employee",
                employee=employee,
            )

        flash(
            "Employee updated successfully.",
            "success",
        )

        return redirect(
            url_for(
                "employees.view_employee",
                employee_id=employee.id,
            )
        )

    return render_template(
        "employees/form.html",
        form=form,
        page_heading="Edit Employee",
        employee=employee,
    )


@employees_bp.route(
    "/<int:employee_id>/toggle-status",
    methods=["POST"],
)
@login_required
def toggle_employee_status(employee_id):
    """Deactivate or reactivate an employee."""

    employee = Employee.query.get_or_404(
        employee_id
    )

    employee.is_active = not employee.is_active

    if employee.is_active:
        if employee.employment_status == "Terminated":
            employee.employment_status = "Active"

        message = (
            "Employee reactivated successfully."
        )

    else:
        employee.employment_status = "Inactive"

        message = (
            "Employee deactivated successfully."
        )

    db.session.commit()

    flash(
        message,
        "success",
    )

    return redirect(
        url_for("employees.list_employees")
    )
