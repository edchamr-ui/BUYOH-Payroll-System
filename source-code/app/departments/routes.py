"""Routes for department management."""

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.auth.permissions import (
    ADMIN,
    MANAGEMENT,
    PAYROLL_OFFICER,
    admin_required,
    roles_required,
)
from app.departments import departments_bp
from app.departments.forms import DepartmentForm
from app.extensions import db
from app.models import Department


@departments_bp.route("/")
@login_required
@roles_required(
    ADMIN,
    PAYROLL_OFFICER,
    MANAGEMENT,
)
def list_departments():
    """Display searchable, filtered and paginated departments."""

    search_term = request.args.get(
        "q",
        "",
    ).strip()

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

    query = Department.query.options(
        selectinload(Department.employees)
    )

    if search_term:
        search_pattern = f"%{search_term}%"

        query = query.filter(
            or_(
                Department.name.ilike(
                    search_pattern
                ),
                Department.description.ilike(
                    search_pattern
                ),
            )
        )

    if status_filter == "active":
        query = query.filter(
            Department.is_active.is_(True)
        )

    elif status_filter == "inactive":
        query = query.filter(
            Department.is_active.is_(False)
        )

    pagination = (
        query
        .order_by(Department.name.asc())
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )
    )

    return render_template(
        "departments/list.html",
        departments=pagination.items,
        pagination=pagination,
        search_term=search_term,
        status_filter=status_filter,
    )


@departments_bp.route(
    "/add",
    methods=["GET", "POST"],
)
@login_required
@admin_required
def add_department():
    """Create a new department."""

    form = DepartmentForm()

    if form.validate_on_submit():
        department_name = form.name.data.strip()

        existing_department = Department.query.filter(
            db.func.lower(Department.name)
            == department_name.lower()
        ).first()

        if existing_department:
            flash(
                "A department with that name already exists.",
                "danger",
            )

        else:
            department = Department(
                name=department_name,
                description=(
                    form.description.data.strip()
                    if form.description.data
                    else None
                ),
                is_active=True,
            )

            db.session.add(department)

            try:
                db.session.commit()

            except IntegrityError:
                db.session.rollback()

                flash(
                    "A department with that name already exists.",
                    "danger",
                )

                return render_template(
                    "departments/form.html",
                    form=form,
                    page_heading="Add Department",
                )

            flash(
                "Department added successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "departments.list_departments"
                )
            )

    return render_template(
        "departments/form.html",
        form=form,
        page_heading="Add Department",
    )


@departments_bp.route(
    "/<int:department_id>/edit",
    methods=["GET", "POST"],
)
@login_required
@admin_required
def edit_department(department_id):
    """Update an existing department."""

    department = Department.query.get_or_404(
        department_id
    )

    form = DepartmentForm(
        obj=department
    )

    if form.validate_on_submit():
        department_name = form.name.data.strip()

        existing_department = (
            Department.query
            .filter(
                db.func.lower(Department.name)
                == department_name.lower(),
                Department.id != department.id,
            )
            .first()
        )

        if existing_department:
            flash(
                "A department with that name already exists.",
                "danger",
            )

            return render_template(
                "departments/form.html",
                form=form,
                page_heading="Edit Department",
                department=department,
            )

        department.name = department_name

        department.description = (
            form.description.data.strip()
            if form.description.data
            else None
        )

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                "A department with that name already exists.",
                "danger",
            )

            return render_template(
                "departments/form.html",
                form=form,
                page_heading="Edit Department",
                department=department,
            )

        flash(
            "Department updated successfully.",
            "success",
        )

        return redirect(
            url_for(
                "departments.list_departments"
            )
        )

    return render_template(
        "departments/form.html",
        form=form,
        page_heading="Edit Department",
        department=department,
    )


@departments_bp.route(
    "/<int:department_id>/toggle-status",
    methods=["POST"],
)
@login_required
@admin_required
def toggle_department_status(department_id):
    """Activate or deactivate a department."""

    department = Department.query.get_or_404(
        department_id
    )

    if department.is_active:
        active_employee_count = sum(
            1
            for employee in department.employees
            if employee.is_active
        )

        if active_employee_count > 0:
            flash(
                (
                    "This department cannot be deactivated "
                    f"because it has {active_employee_count} "
                    "active employee"
                    f"{'s' if active_employee_count != 1 else ''}."
                ),
                "danger",
            )

            return redirect(
                url_for(
                    "departments.list_departments"
                )
            )

        department.is_active = False
        message = "Department deactivated successfully."

    else:
        department.is_active = True
        message = "Department reactivated successfully."

    db.session.commit()

    flash(
        message,
        "success",
    )

    return redirect(
        url_for(
            "departments.list_departments"
        )
    )
