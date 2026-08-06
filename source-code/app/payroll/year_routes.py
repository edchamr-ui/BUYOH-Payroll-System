"""Payroll-year routes integrated into the payroll blueprint."""

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
from app.payroll import payroll_bp
from app.payroll.year_forms import (
    PayrollYearCreateForm,
)
from app.services.payroll_year_service import (
    PayrollYearAlreadyExistsError,
    PayrollYearCreationError,
    PayrollYearService,
)


@payroll_bp.route("/years")
@login_required
@admin_required
def payroll_years():
    """Display annual payroll calendars."""

    years = (
        PayrollYear.query
        .order_by(
            PayrollYear.year.desc()
        )
        .all()
    )

    return render_template(
        "payroll/years/index.html",
        payroll_years=years,
    )


@payroll_bp.route(
    "/years/new",
    methods=["GET", "POST"],
)
@login_required
@admin_required
def create_payroll_year():
    """Create one payroll year and twelve monthly periods."""

    form = PayrollYearCreateForm()

    if form.validate_on_submit():
        try:
            result = PayrollYearService.create_year(
                year=form.year.data,
                payment_day=form.payment_day.data,
                created_by_user_id=current_user.id,
                clamp_payment_day=bool(
                    form.clamp_payment_day.data
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
                    "payroll.view_payroll_year",
                    payroll_year_id=(
                        result.payroll_year.id
                    ),
                )
            )

    return render_template(
        "payroll/years/form.html",
        form=form,
    )


@payroll_bp.route(
    "/years/<int:payroll_year_id>"
)
@login_required
@admin_required
def view_payroll_year(
    payroll_year_id,
):
    """Display one payroll year and its monthly calendar."""

    payroll_year = PayrollYear.query.get_or_404(
        payroll_year_id
    )

    return render_template(
        "payroll/years/view.html",
        payroll_year=payroll_year,
    )
