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
from app.models.payroll_ssp_input import PayrollSSPInput
from app.models.payroll_smp_input import PayrollSMPInput
from app.models.payroll_spp_input import PayrollSPPInput
from app.payroll_periods import payroll_periods_bp
from app.payroll_periods.forms import (
    PayrollPeriodActionForm,
    PayrollPeriodForm,
    PayrollSSPInputForm,
    PayrollSMPInputForm,
    PayrollSPPInputForm,
)


def can_manage_ssp(period):
    """Return whether operational SSP inputs may still be changed."""

    return (
        period.status == "Draft"
        and period.payroll_year is not None
        and period.payroll_year.is_open
    )


def can_manage_smp(period):
    """Return whether operational SMP inputs may still be changed."""

    return can_manage_ssp(period)


def validate_smp_dates(form, period):
    """Return period-aware validation messages for an SMP input."""

    maternity_start = form.maternity_pay_period_start.data
    if maternity_start is None:
        return []

    if maternity_start > period.end_date:
        return [
            "Maternity pay period start cannot be after the payroll period end date."
        ]

    return []


def can_manage_spp(period):
    """Return whether operational SPP inputs may still be changed."""

    return can_manage_ssp(period)


def validate_spp_dates(form, period):
    """Return period-aware validation messages for an SPP input."""

    paternity_start = form.paternity_pay_period_start.data
    if paternity_start is None:
        return []
    if paternity_start > period.end_date:
        return [
            "Paternity pay period start cannot be after the payroll period end date."
        ]
    return []


def validate_ssp_dates(form, period):
    """Return period-aware validation messages for a sickness input."""

    sickness_start = form.sickness_start_date.data
    if sickness_start is None:
        return []

    if sickness_start > period.end_date:
        return [
            "Sickness start date cannot be after the payroll period end date."
        ]

    return []


def get_uk_employee_or_404(employee_id):
    """Resolve an employee who has an enabled UK payroll profile."""

    return (
        Employee.query
        .filter(Employee.id == employee_id)
        .filter(Employee.uk_tax_profile.has())
        .first_or_404()
    )


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


@payroll_periods_bp.route("/<int:period_id>/ssp")
@login_required
def list_ssp_inputs(period_id):
    """List UK employees and their SSP inputs for one payroll period."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employees = (
        Employee.query
        .filter(Employee.uk_tax_profile.has())
        .filter(Employee.is_active.is_(True))
        .order_by(Employee.last_name, Employee.first_name)
        .all()
    )
    saved_inputs = {
        item.employee_id: item
        for item in PayrollSSPInput.query.filter_by(
            payroll_period_id=period.id
        ).all()
    }

    return render_template(
        "payroll_periods/ssp_inputs.html",
        period=period,
        employees=employees,
        saved_inputs=saved_inputs,
        can_edit=can_manage_ssp(period),
        action_form=PayrollPeriodActionForm(),
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/ssp/<int:employee_id>",
    methods=["GET", "POST"],
)
@login_required
def edit_ssp_input(period_id, employee_id):
    """Create or update one UK employee's Draft-period SSP input."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employee = get_uk_employee_or_404(employee_id)

    if not can_manage_ssp(period):
        flash("SSP inputs can only be changed in an open Draft period.", "warning")
        return redirect(
            url_for("payroll_periods.list_ssp_inputs", period_id=period.id)
        )

    ssp_input = PayrollSSPInput.query.filter_by(
        payroll_period_id=period.id,
        employee_id=employee.id,
    ).first()
    form = PayrollSSPInputForm(obj=ssp_input)

    if form.validate_on_submit():
        date_errors = validate_ssp_dates(form, period)
        if date_errors:
            for error in date_errors:
                form.sickness_start_date.errors.append(error)
        else:
            if ssp_input is None:
                ssp_input = PayrollSSPInput(
                    payroll_period_id=period.id,
                    employee_id=employee.id,
                )
                db.session.add(ssp_input)

            ssp_input.sickness_start_date = form.sickness_start_date.data
            ssp_input.average_weekly_earnings = form.average_weekly_earnings.data
            ssp_input.qualifying_days_per_week = (
                form.qualifying_days_per_week.data
            )
            ssp_input.qualifying_days_sick = form.qualifying_days_sick.data
            ssp_input.salary_withheld = form.salary_withheld.data
            ssp_input.notes = (form.notes.data or "").strip() or None
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("The SSP input could not be saved. Please try again.", "danger")
            else:
                flash(f"SSP input saved for {employee.full_name}.", "success")
                return redirect(
                    url_for("payroll_periods.list_ssp_inputs", period_id=period.id)
                )

    return render_template(
        "payroll_periods/ssp_form.html",
        period=period,
        employee=employee,
        form=form,
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/ssp/<int:employee_id>/delete",
    methods=["POST"],
)
@login_required
def delete_ssp_input(period_id, employee_id):
    """Delete one SSP input while its payroll period remains editable."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employee = get_uk_employee_or_404(employee_id)
    form = PayrollPeriodActionForm()

    if not form.validate_on_submit():
        flash("The SSP deletion request was invalid.", "danger")
    elif not can_manage_ssp(period):
        flash("SSP inputs can only be deleted in an open Draft period.", "warning")
    else:
        ssp_input = PayrollSSPInput.query.filter_by(
            payroll_period_id=period.id,
            employee_id=employee.id,
        ).first()
        if ssp_input is not None:
            db.session.delete(ssp_input)
            db.session.commit()
            flash(f"SSP input removed for {employee.full_name}.", "success")

    return redirect(
        url_for("payroll_periods.list_ssp_inputs", period_id=period.id)
    )


@payroll_periods_bp.route("/<int:period_id>/smp")
@login_required
def list_smp_inputs(period_id):
    """List UK employees and their SMP inputs for one payroll period."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employees = (
        Employee.query
        .filter(Employee.uk_tax_profile.has())
        .filter(Employee.is_active.is_(True))
        .order_by(Employee.last_name, Employee.first_name)
        .all()
    )
    saved_inputs = {
        item.employee_id: item
        for item in PayrollSMPInput.query.filter_by(
            payroll_period_id=period.id
        ).all()
    }

    return render_template(
        "payroll_periods/smp_inputs.html",
        period=period,
        employees=employees,
        saved_inputs=saved_inputs,
        can_edit=can_manage_smp(period),
        action_form=PayrollPeriodActionForm(),
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/smp/<int:employee_id>",
    methods=["GET", "POST"],
)
@login_required
def edit_smp_input(period_id, employee_id):
    """Create or update one UK employee's Draft-period SMP input."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employee = get_uk_employee_or_404(employee_id)

    if not can_manage_smp(period):
        flash("SMP inputs can only be changed in an open Draft period.", "warning")
        return redirect(
            url_for("payroll_periods.list_smp_inputs", period_id=period.id)
        )

    smp_input = PayrollSMPInput.query.filter_by(
        payroll_period_id=period.id,
        employee_id=employee.id,
    ).first()
    form = PayrollSMPInputForm(obj=smp_input)

    if form.validate_on_submit():
        date_errors = validate_smp_dates(form, period)
        if date_errors:
            for error in date_errors:
                form.maternity_pay_period_start.errors.append(error)
        else:
            if smp_input is None:
                smp_input = PayrollSMPInput(
                    payroll_period_id=period.id,
                    employee_id=employee.id,
                )
                db.session.add(smp_input)

            smp_input.maternity_pay_period_start = (
                form.maternity_pay_period_start.data
            )
            smp_input.average_weekly_earnings = form.average_weekly_earnings.data
            smp_input.paid_days = form.paid_days.data
            smp_input.salary_withheld = form.salary_withheld.data
            smp_input.eligibility_confirmed = form.eligibility_confirmed.data
            smp_input.matb1_received = form.matb1_received.data
            smp_input.notes = (form.notes.data or "").strip() or None
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("The SMP input could not be saved. Please try again.", "danger")
            else:
                flash(f"SMP input saved for {employee.full_name}.", "success")
                return redirect(
                    url_for("payroll_periods.list_smp_inputs", period_id=period.id)
                )

    return render_template(
        "payroll_periods/smp_form.html",
        period=period,
        employee=employee,
        form=form,
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/smp/<int:employee_id>/delete",
    methods=["POST"],
)
@login_required
def delete_smp_input(period_id, employee_id):
    """Delete one SMP input while its payroll period remains editable."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employee = get_uk_employee_or_404(employee_id)
    form = PayrollPeriodActionForm()

    if not form.validate_on_submit():
        flash("The SMP deletion request was invalid.", "danger")
    elif not can_manage_smp(period):
        flash("SMP inputs can only be deleted in an open Draft period.", "warning")
    else:
        smp_input = PayrollSMPInput.query.filter_by(
            payroll_period_id=period.id,
            employee_id=employee.id,
        ).first()
        if smp_input is not None:
            db.session.delete(smp_input)
            db.session.commit()
            flash(f"SMP input removed for {employee.full_name}.", "success")

    return redirect(
        url_for("payroll_periods.list_smp_inputs", period_id=period.id)
    )


@payroll_periods_bp.route("/<int:period_id>/spp")
@login_required
def list_spp_inputs(period_id):
    """List UK employees and their SPP inputs for one payroll period."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employees = (
        Employee.query
        .filter(Employee.uk_tax_profile.has())
        .filter(Employee.is_active.is_(True))
        .order_by(Employee.last_name, Employee.first_name)
        .all()
    )
    saved_inputs = {
        item.employee_id: item
        for item in PayrollSPPInput.query.filter_by(
            payroll_period_id=period.id
        ).all()
    }
    return render_template(
        "payroll_periods/spp_inputs.html",
        period=period,
        employees=employees,
        saved_inputs=saved_inputs,
        can_edit=can_manage_spp(period),
        action_form=PayrollPeriodActionForm(),
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/spp/<int:employee_id>", methods=["GET", "POST"]
)
@login_required
def edit_spp_input(period_id, employee_id):
    """Create or update one UK employee's Draft-period SPP input."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employee = get_uk_employee_or_404(employee_id)
    if not can_manage_spp(period):
        flash("SPP inputs can only be changed in an open Draft period.", "warning")
        return redirect(
            url_for("payroll_periods.list_spp_inputs", period_id=period.id)
        )

    spp_input = PayrollSPPInput.query.filter_by(
        payroll_period_id=period.id,
        employee_id=employee.id,
    ).first()
    form = PayrollSPPInputForm(obj=spp_input)

    if form.validate_on_submit():
        date_errors = validate_spp_dates(form, period)
        if date_errors:
            for error in date_errors:
                form.paternity_pay_period_start.errors.append(error)
        else:
            if spp_input is None:
                spp_input = PayrollSPPInput(
                    payroll_period_id=period.id,
                    employee_id=employee.id,
                )
                db.session.add(spp_input)

            spp_input.paternity_pay_period_start = (
                form.paternity_pay_period_start.data
            )
            spp_input.average_weekly_earnings = form.average_weekly_earnings.data
            spp_input.paid_days = form.paid_days.data
            spp_input.salary_withheld = form.salary_withheld.data
            spp_input.eligibility_confirmed = form.eligibility_confirmed.data
            spp_input.declaration_received = form.declaration_received.data
            spp_input.notes = (form.notes.data or "").strip() or None
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("The SPP input could not be saved. Please try again.", "danger")
            else:
                flash(f"SPP input saved for {employee.full_name}.", "success")
                return redirect(
                    url_for("payroll_periods.list_spp_inputs", period_id=period.id)
                )

    return render_template(
        "payroll_periods/spp_form.html",
        period=period,
        employee=employee,
        form=form,
        month_name=month_name,
    )


@payroll_periods_bp.route(
    "/<int:period_id>/spp/<int:employee_id>/delete", methods=["POST"]
)
@login_required
def delete_spp_input(period_id, employee_id):
    """Delete one SPP input while its payroll period remains editable."""

    period = PayrollPeriod.query.get_or_404(period_id)
    employee = get_uk_employee_or_404(employee_id)
    form = PayrollPeriodActionForm()
    if not form.validate_on_submit():
        flash("The SPP deletion request was invalid.", "danger")
    elif not can_manage_spp(period):
        flash("SPP inputs can only be deleted in an open Draft period.", "warning")
    else:
        spp_input = PayrollSPPInput.query.filter_by(
            payroll_period_id=period.id,
            employee_id=employee.id,
        ).first()
        if spp_input is not None:
            db.session.delete(spp_input)
            db.session.commit()
            flash(f"SPP input removed for {employee.full_name}.", "success")

    return redirect(
        url_for("payroll_periods.list_spp_inputs", period_id=period.id)
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
