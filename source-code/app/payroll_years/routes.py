"""Payroll year management routes."""

from flask import (
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)

from app.auth.permissions import admin_required
from app.models import PayrollYear
from app.payroll_years import payroll_years_bp
from app.payroll_years.forms import (
    PayrollYearCreateForm,
)
from app.services.payroll_year_service import (
    PayrollYearAlreadyExistsError,
    PayrollYearCreationError,
    PayrollYearService,
)


@payroll_years_bp.route("/")
@login_required
@admin_required
def index():
    """Display all payroll years."""

    payroll_years = (
        PayrollYear.query
        .order_by(
            PayrollYear.year.desc()
        )
        .all()
    )

    return render_template(
        "payroll_years/index.html",
        payroll_years=payroll_years,
    )


@payroll_years_bp.route(
    "/new",
    methods=["GET", "POST"],
)
@login_required
@admin_required
def create():
    """Create a payroll year and all 12 monthly periods."""

    form = PayrollYearCreateForm()

    if form.validate_on_submit():
        try:
            result = PayrollYearService.create_year(
                year=form.year.data,
                payment_day=form.payment_day.data,
                created_by_user_id=current_user.id,
                clamp_payment_day=bool(
                    form.allow_payment_after_month_end.data
                ),
            )

        except PayrollYearAlreadyExistsError as error:
            flash(
                str(error),
                "warning",
            )

        except PayrollYearCreationError as error:
            flash(
                str(error),
                "danger",
            )

        else:
            flash(
                (
                    f"Payroll year {result.payroll_year.year} "
                    f"was created successfully with "
                    f"{result.created_period_count} monthly periods."
                ),
                "success",
            )

            return redirect(
                url_for(
                    "payroll_years.view",
                    payroll_year_id=(
                        result.payroll_year.id
                    ),
                )
            )

    return render_template(
        "payroll_years/form.html",
        form=form,
    )


@payroll_years_bp.route(
    "/<int:payroll_year_id>",
)
@login_required
@admin_required
def view(payroll_year_id):
    """Display one payroll year and its monthly calendar."""

    payroll_year = PayrollYear.query.get_or_404(
        payroll_year_id
    )

    return render_template(
        "payroll_years/view.html",
        payroll_year=payroll_year,
    )
