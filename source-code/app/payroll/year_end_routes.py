"""Payroll year-end routes integrated into the payroll blueprint."""

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)

from app.auth.permissions import admin_required
from app.models import PayrollYear
from app.payroll import payroll_bp
from app.payroll.year_end_forms import (
    PayrollYearCloseForm,
)
from app.services.payroll_year_end_service import (
    PayrollYearEndError,
    PayrollYearEndService,
)


@payroll_bp.route(
    "/years/<int:payroll_year_id>/year-end",
)
@login_required
@admin_required
def review_payroll_year_end(
    payroll_year_id,
):
    """Display year-end validation and closing controls."""

    payroll_year = PayrollYear.query.get_or_404(
        payroll_year_id
    )

    validation = PayrollYearEndService.validate_year(
        payroll_year
    )

    form = PayrollYearCloseForm()

    return render_template(
        "payroll/year_end/review.html",
        payroll_year=payroll_year,
        validation=validation,
        form=form,
        expected_phrase=(
            PayrollYearEndService.EXPECTED_CONFIRMATION
        ),
    )


@payroll_bp.route(
    "/years/<int:payroll_year_id>/year-end/close",
    methods=["POST"],
)
@login_required
@admin_required
def close_payroll_year(
    payroll_year_id,
):
    """Close one validated payroll year."""

    payroll_year = PayrollYear.query.get_or_404(
        payroll_year_id
    )

    form = PayrollYearCloseForm()

    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "danger")

        return redirect(
            url_for(
                "payroll.review_payroll_year_end",
                payroll_year_id=payroll_year.id,
            )
        )

    if not current_user.check_password(
        form.current_password.data
    ):
        flash(
            "The administrator password is incorrect.",
            "danger",
        )

        return redirect(
            url_for(
                "payroll.review_payroll_year_end",
                payroll_year_id=payroll_year.id,
            )
        )

    if (
        form.confirmation_phrase.data.strip()
        != PayrollYearEndService.EXPECTED_CONFIRMATION
    ):
        flash(
            (
                'Type "CLOSE PAYROLL YEAR" exactly '
                "to confirm."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.review_payroll_year_end",
                payroll_year_id=payroll_year.id,
            )
        )

    try:
        PayrollYearEndService.close_year(
            payroll_year=payroll_year,
            closed_by_user_id=current_user.id,
            closing_reason=form.closing_reason.data,
        )

    except PayrollYearEndError as error:
        flash(
            str(error),
            "danger",
        )

    else:
        flash(
            (
                f"Payroll year {payroll_year.year} "
                "was closed successfully."
            ),
            "success",
        )

    return redirect(
        url_for(
            "payroll.view_payroll_year",
            payroll_year_id=payroll_year.id,
        )
    )
