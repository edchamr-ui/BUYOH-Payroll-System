from flask import flash, redirect, render_template, url_for
from flask_login import login_required

from app.departments import departments_bp
from app.departments.forms import DepartmentForm
from app.extensions import db
from app.models import Department


@departments_bp.route("/")
@login_required
def list_departments():
    departments = Department.query.order_by(
        Department.name.asc()
    ).all()

    return render_template(
        "departments/list.html",
        departments=departments,
    )


@departments_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_department():
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
            db.session.commit()

            flash(
                "Department added successfully.",
                "success",
            )

            return redirect(
                url_for("departments.list_departments")
            )

    return render_template(
        "departments/form.html",
        form=form,
        page_heading="Add Department",
    )
