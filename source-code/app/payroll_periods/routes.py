from calendar import month_name
from datetime import datetime, timedelta

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
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import PayrollPeriod
from app.payroll_periods import payroll_periods_bp
from app.payroll_periods.forms import (
    PayrollPeriodActionForm,
    PayrollPeriodForm,
)


STATUS_TRANSITIONS = {
    "Draft": "Processing",
    "Processing": "Approved",
    "Approved": "Paid",
    "Paid": "Locked",
}


def validate_period_dates(form):
    """
    Validate payroll period dates.

    Start and end dates must belong to the selected payroll
    month and year. Payment may occur during the period or
    within 31 days after the period ends.
    """

    errors = []

    selected_month = form.month.data
    selected_year = form.year.data

    start_date = form.start_date.data
    end_date = form.end_date.data
    payment_date = form.payment_date.data

    if not all(
        [
            selected_month,
            selected_year,
            start_date,
            end_date,
            payment_date,
        ]
    ):
        return errors

    if (
        start_date.month != selected_month
        or start_date.year != selected_year
    ):
        errors.append(
            "The start date must belong to the selected "
            "payroll month and year."
        )

    if (
        end_date.month != selected_month
        or end_date.year != selected_year
    ):
        errors.append(
            "The end date must belong to the selected "
            "payroll month and year."
        )

    if end_date < start_date:
        errors.append(
            "The end date cannot be earlier than the start date."
        )

    latest_payment_date = end_date + timedelta(days=31)

    if payment_date < start_date:
        errors.append(
            "The payment date cannot be earlier than "
            "the payroll start date."
        )

    if payment_date > latest_payment_date:
        errors.append(
            "The payment date cannot be more than 31 days "
            "after the payroll period ends."
        )

    return errors


@payroll_periods_bp.route("/")
@login_required
def list_periods():
    """Display all payroll periods."""

    periods = PayrollPeriod.query.order_by(
        PayrollPeriod.year.desc(),
        PayrollPeriod.month.desc(),
    ).all()

    return render_template(
        "payroll_periods/list.html",
        periods=periods,
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/add",
    methods=["GET", "POST"],
)
@login_required
def add_period():
    """Create a new payroll period."""

    form = PayrollPeriodForm()

    if form.validate_on_submit():
        date_errors = validate_period_dates(form)

        if date_errors:
            for error in date_errors:
                flash(error, "danger")

            return render_template(
                "payroll_periods/form.html",
                form=form,
                page_heading="Add Payroll Period",
            )

        existing_period = PayrollPeriod.query.filter_by(
            month=form.month.data,
            year=form.year.data,
        ).first()

        if existing_period:
            flash(
                "A payroll period already exists for that "
                "month and year.",
                "danger",
            )

            return render_template(
                "payroll_periods/form.html",
                form=form,
                page_heading="Add Payroll Period",
            )

        period = PayrollPeriod(
            month=form.month.data,
            year=form.year.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            payment_date=form.payment_date.data,
            status="Draft",
            created_by=current_user.id,
        )

        db.session.add(period)

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                "The payroll period could not be created "
                "because it conflicts with an existing record.",
                "danger",
            )

            return render_template(
                "payroll_periods/form.html",
                form=form,
                page_heading="Add Payroll Period",
            )

        flash(
            "Payroll period created successfully.",
            "success",
        )

        return redirect(
            url_for("payroll_periods.list_periods")
        )

    return render_template(
        "payroll_periods/form.html",
        form=form,
        page_heading="Add Payroll Period",
    )


@payroll_periods_bp.route("/<int:period_id>")
@login_required
def view_period(period_id):
    """Display one payroll period."""

    period = PayrollPeriod.query.get_or_404(period_id)

    action_form = PayrollPeriodActionForm()

    next_status = STATUS_TRANSITIONS.get(period.status)

    return render_template(
        "payroll_periods/view.html",
        period=period,
        month_name=month_name,
        action_form=action_form,
        next_status=next_status,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_period(period_id):
    """Edit a payroll period while it remains in Draft."""

    period = PayrollPeriod.query.get_or_404(period_id)

    if period.status != "Draft":
        flash(
            "Only Draft payroll periods can be edited.",
            "warning",
        )

        return redirect(
            url_for(
                "payroll_periods.view_period",
                period_id=period.id,
            )
        )

    form = PayrollPeriodForm(obj=period)

    if form.validate_on_submit():
        date_errors = validate_period_dates(form)

        if date_errors:
            for error in date_errors:
                flash(error, "danger")

            return render_template(
                "payroll_periods/form.html",
                form=form,
                page_heading="Edit Payroll Period",
                period=period,
            )

        duplicate_period = PayrollPeriod.query.filter(
            PayrollPeriod.month == form.month.data,
            PayrollPeriod.year == form.year.data,
            PayrollPeriod.id != period.id,
        ).first()

        if duplicate_period:
            flash(
                "Another payroll period already exists for "
                "that month and year.",
                "danger",
            )

            return render_template(
                "payroll_periods/form.html",
                form=form,
                page_heading="Edit Payroll Period",
                period=period,
            )

        period.month = form.month.data
        period.year = form.year.data
        period.start_date = form.start_date.data
        period.end_date = form.end_date.data
        period.payment_date = form.payment_date.data

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                "The payroll period could not be updated.",
                "danger",
            )

            return render_template(
                "payroll_periods/form.html",
                form=form,
                page_heading="Edit Payroll Period",
                period=period,
            )

        flash(
            "Payroll period updated successfully.",
            "success",
        )

        return redirect(
            url_for(
                "payroll_periods.view_period",
                period_id=period.id,
            )
        )

    return render_template(
        "payroll_periods/form.html",
        form=form,
        page_heading="Edit Payroll Period",
        period=period,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/advance-status",
    methods=["POST"],
)
@login_required
def advance_status(period_id):
    """Advance a payroll period through its workflow."""

    period = PayrollPeriod.query.get_or_404(period_id)

    form = PayrollPeriodActionForm()

    if not form.validate_on_submit():
        flash(
            "The payroll status request could not be validated.",
            "danger",
        )

        return redirect(
            url_for(
                "payroll_periods.view_period",
                period_id=period.id,
            )
        )

    next_status = STATUS_TRANSITIONS.get(period.status)

    if not next_status:
        flash(
            "This payroll period is already locked.",
            "warning",
        )

        return redirect(
            url_for(
                "payroll_periods.view_period",
                period_id=period.id,
            )
        )

    previous_status = period.status
    period.status = next_status

    if next_status == "Approved":
        period.approved_by = current_user.id
        period.approved_at = datetime.utcnow()

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

        flash(
            "The payroll period status could not be updated.",
            "danger",
        )

        return redirect(
            url_for(
                "payroll_periods.view_period",
                period_id=period.id,
            )
        )

    flash(
        f"Payroll period moved from {previous_status} "
        f"to {next_status}.",
        "success",
    )

    return redirect(
        url_for(
            "payroll_periods.view_period",
            period_id=period.id,
        )
    )
