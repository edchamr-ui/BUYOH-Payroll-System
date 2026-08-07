"""Payroll period management routes."""

from calendar import month_name
from datetime import timedelta

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
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import (
    Employee,
    PayrollPeriod,
    PayrollYear,
)
from app.payroll_periods import payroll_periods_bp
from app.payroll_periods.forms import PayrollPeriodForm


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


def get_open_payroll_year(year):
    """
    Return an open PayrollYear parent for the supplied year.

    Individual periods cannot exist without a parent payroll year.
    """

    return PayrollYear.query.filter_by(
        year=year,
        status=PayrollYear.STATUS_OPEN,
    ).first()


@payroll_periods_bp.route("/")
@login_required
def list_periods():
    """Display the payroll operations dashboard."""

    periods = (
        PayrollPeriod.query
        .options(
            selectinload(
                PayrollPeriod.payroll_records
            )
        )
        .order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc(),
        )
        .all()
    )

    period_rows = []
    total_gross_payroll = 0
    total_net_payroll = 0
    total_payslips = 0
    total_payroll_records = 0

    workflow_map = {
        "Draft": {
            "label": "Ready for processing",
            "button": "Process Payroll",
            "icon": "play-circle",
            "button_class": "btn-primary",
        },
        "Processing": {
            "label": "Processing in progress",
            "button": "Continue Processing",
            "icon": "hourglass-split",
            "button_class": "btn-warning",
        },
        "Processed": {
            "label": "Awaiting review",
            "button": "Review Payroll",
            "icon": "clipboard-check",
            "button_class": "btn-outline-primary",
        },
        "Approved": {
            "label": "Ready to lock",
            "button": "Open and Lock",
            "icon": "lock",
            "button_class": "btn-outline-success",
        },
        "Paid": {
            "label": "Payment completed",
            "button": "View Register",
            "icon": "cash-coin",
            "button_class": "btn-outline-success",
        },
        "Locked": {
            "label": "Completed and protected",
            "button": "View Register",
            "icon": "eye",
            "button_class": "btn-outline-dark",
        },
    }

    for period in periods:
        records = list(
            period.payroll_records or []
        )

        employee_count = len(records)

        gross_payroll = sum(
            record.gross_pay or 0
            for record in records
        )

        net_payroll = sum(
            record.net_pay or 0
            for record in records
        )

        payslip_count = sum(
            1
            for record in records
            if record.payslip is not None
        )

        total_gross_payroll += gross_payroll
        total_net_payroll += net_payroll
        total_payslips += payslip_count
        total_payroll_records += employee_count

        workflow = workflow_map.get(
            period.status,
            {
                "label": "Review payroll status",
                "button": "Open Payroll",
                "icon": "cash-stack",
                "button_class": "btn-outline-primary",
            },
        )

        period_rows.append(
            {
                "period": period,
                "employee_count": employee_count,
                "gross_payroll": gross_payroll,
                "net_payroll": net_payroll,
                "payslip_count": payslip_count,
                "workflow": workflow,
            }
        )

    dashboard = {
        "payroll_years": PayrollYear.query.count(),
        "active_employees": (
            Employee.query
            .filter(
                Employee.is_active.is_(True)
            )
            .count()
        ),
        "total_periods": len(periods),
        "draft_periods": sum(
            1
            for period in periods
            if period.status == "Draft"
        ),
        "processed_periods": sum(
            1
            for period in periods
            if period.status == "Processed"
        ),
        "approved_periods": sum(
            1
            for period in periods
            if period.status == "Approved"
        ),
        "locked_periods": sum(
            1
            for period in periods
            if period.status == "Locked"
        ),
        "total_payroll_records": total_payroll_records,
        "total_payslips": total_payslips,
        "total_gross_payroll": total_gross_payroll,
        "total_net_payroll": total_net_payroll,
    }

    return render_template(
        "payroll_periods/list.html",
        period_rows=period_rows,
        dashboard=dashboard,
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/add",
    methods=["GET", "POST"],
)
@login_required
def add_period():
    """
    Create an individual payroll period under an existing open year.

    The normal workflow creates all twelve periods through the
    Payroll Year generator. This route remains available only for
    replacing a missing period.
    """

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

        payroll_year = get_open_payroll_year(
            form.year.data
        )

        if payroll_year is None:
            flash(
                (
                    f"An open payroll year for {form.year.data} "
                    "does not exist. Create the payroll year first."
                ),
                "warning",
            )

            return redirect(
                url_for(
                    "payroll.create_payroll_year"
                )
            )

        existing_period = PayrollPeriod.query.filter_by(
            payroll_year_id=payroll_year.id,
            month=form.month.data,
        ).first()

        if existing_period:
            flash(
                (
                    f"{month_name[form.month.data]} "
                    f"{form.year.data} already exists in the "
                    "payroll calendar."
                ),
                "warning",
            )

            return redirect(
                url_for(
                    "payroll.view_payroll_year",
                    payroll_year_id=payroll_year.id,
                )
            )

        period = PayrollPeriod(
            payroll_year_id=payroll_year.id,
            month=form.month.data,
            year=payroll_year.year,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            payment_date=form.payment_date.data,
            status="Draft",
            created_by=current_user.id,
        )

        db.session.add(period)

        try:
            db.session.commit()

        except IntegrityError as error:
            db.session.rollback()

            flash(
                (
                    "The payroll period could not be created. "
                    "A period for that month may already exist."
                ),
                "danger",
            )

            # During development, this records the real database
            # exception in the Flask terminal.
            print(
                "Payroll period creation IntegrityError:",
                error,
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
            url_for(
                "payroll.view_payroll_year",
                payroll_year_id=payroll_year.id,
            )
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

    period = PayrollPeriod.query.get_or_404(
        period_id
    )

    return render_template(
        "payroll_periods/view.html",
        period=period,
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_period(period_id):
    """Edit a payroll period while it remains in Draft."""

    period = PayrollPeriod.query.get_or_404(
        period_id
    )

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

    if (
        period.payroll_year is None
        or not period.payroll_year.is_open
    ):
        flash(
            (
                "This payroll period cannot be edited because "
                "its payroll year is not open."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "payroll_periods.view_period",
                period_id=period.id,
            )
        )

    form = PayrollPeriodForm(
        obj=period
    )

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

        target_payroll_year = get_open_payroll_year(
            form.year.data
        )

        if target_payroll_year is None:
            flash(
                (
                    f"An open payroll year for {form.year.data} "
                    "does not exist."
                ),
                "danger",
            )

            return render_template(
                "payroll_periods/form.html",
                form=form,
                page_heading="Edit Payroll Period",
                period=period,
            )

        duplicate_period = PayrollPeriod.query.filter(
            PayrollPeriod.payroll_year_id
            == target_payroll_year.id,
            PayrollPeriod.month
            == form.month.data,
            PayrollPeriod.id
            != period.id,
        ).first()

        if duplicate_period:
            flash(
                (
                    f"{month_name[form.month.data]} "
                    f"{form.year.data} already exists in the "
                    "payroll calendar."
                ),
                "danger",
            )

            return render_template(
                "payroll_periods/form.html",
                form=form,
                page_heading="Edit Payroll Period",
                period=period,
            )

        period.payroll_year_id = (
            target_payroll_year.id
        )
        period.month = form.month.data
        period.year = target_payroll_year.year
        period.start_date = form.start_date.data
        period.end_date = form.end_date.data
        period.payment_date = form.payment_date.data

        try:
            db.session.commit()

        except IntegrityError as error:
            db.session.rollback()

            flash(
                (
                    "The payroll period could not be updated "
                    "because the resulting month already exists."
                ),
                "danger",
            )

            print(
                "Payroll period update IntegrityError:",
                error,
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
