from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from flask_login import login_required
from sqlalchemy.exc import IntegrityError
from app.employees import employees_bp
from app.employees.forms import EmployeeForm
from app.extensions import db
from app.models import Department, Employee


def load_department_choices(form):
    """Populate the department dropdown from active departments."""

    departments = Department.query.filter_by(
        is_active=True
    ).order_by(Department.name.asc()).all()

    form.department_id.choices = [
        (department.id, department.name)
        for department in departments
    ]


@employees_bp.route("/")
@login_required
def list_employees():
    """Display employees with optional search filtering."""

    search_term = request.args.get("q", "").strip()

    query = Employee.query

    if search_term:
        search_pattern = f"%{search_term}%"

        query = query.filter(
            or_(
                Employee.employee_number.ilike(search_pattern),
                Employee.first_name.ilike(search_pattern),
                Employee.last_name.ilike(search_pattern),
                Employee.national_id.ilike(search_pattern),
                Employee.job_title.ilike(search_pattern),
            )
        )

    employees = query.order_by(
        Employee.first_name.asc(),
        Employee.last_name.asc(),
    ).all()

    return render_template(
        "employees/list.html",
        employees=employees,
        search_term=search_term,
    )


@employees_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_employee():
    """Create a new employee."""

    form = EmployeeForm()
    load_department_choices(form)

    if form.validate_on_submit():
        employee = Employee(
            employee_number=form.employee_number.data.strip(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            national_id=(
                form.national_id.data.strip()
                if form.national_id.data
                else None
            ),
            job_title=form.job_title.data.strip(),
            department_id=form.department_id.data,
            employment_date=form.employment_date.data,
            basic_salary=form.basic_salary.data,
            employment_status=form.employment_status.data,
            is_active=form.employment_status.data != "Terminated",
        )

        db.session.add(employee)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            flash(
                "Employee number or national ID already exists.",
                "danger",
            )

            return render_template(
                "employees/form.html",
                form=form,
                page_heading="Add Employee",
            )

        flash("Employee added successfully.", "success")

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
    """Display a single employee record."""

    employee = Employee.query.get_or_404(employee_id)

    return render_template(
        "employees/view.html",
        employee=employee,
    )


@employees_bp.route(
    "/<int:employee_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_employee(employee_id):
    """Update an existing employee record."""

    employee = Employee.query.get_or_404(employee_id)

    form = EmployeeForm(obj=employee)
    load_department_choices(form)

    if form.validate_on_submit():
        employee.employee_number = (
            form.employee_number.data.strip()
        )

        employee.first_name = form.first_name.data.strip()
        employee.last_name = form.last_name.data.strip()

        employee.national_id = (
            form.national_id.data.strip()
            if form.national_id.data
            else None
        )

        employee.job_title = form.job_title.data.strip()
        employee.department_id = form.department_id.data
        employee.employment_date = form.employment_date.data
        employee.basic_salary = form.basic_salary.data

        employee.employment_status = (
            form.employment_status.data
        )

        employee.is_active = (
            form.employment_status.data != "Terminated"
        )

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            flash(
                "Employee number or national ID already exists.",
                "danger",
            )

            return render_template(
                "employees/form.html",
                form=form,
                page_heading="Edit Employee",
                employee=employee,
            )

        flash("Employee updated successfully.", "success")

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

    employee = Employee.query.get_or_404(employee_id)

    employee.is_active = not employee.is_active

    if employee.is_active:
        if employee.employment_status == "Terminated":
            employee.employment_status = "Active"

        message = "Employee reactivated successfully."
    else:
        employee.employment_status = "Inactive"
        message = "Employee deactivated successfully."

    db.session.commit()

    flash(message, "success")

    return redirect(
        url_for("employees.list_employees")
    )
