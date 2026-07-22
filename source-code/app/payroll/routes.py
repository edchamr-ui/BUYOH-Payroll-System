"""Payroll routes."""

from pathlib import Path

from flask import (
    flash,
    redirect,
    render_template,
    send_file,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)

from app.models import (
    PayrollPeriod,
    PayrollRecord,
    Payslip,
)
from app.payroll import payroll_bp
from app.payroll.forms import PayrollProcessForm
from app.services.payroll_service import (
    InvalidPayrollStatusError,
    NoActiveEmployeesError,
    PayrollPersistenceError,
    PayrollService,
)
from app.services.payslip_service import (
    PayslipGenerationError,
    PayslipRecordNotFoundError,
    PayslipService,
)


@payroll_bp.route("/")
@login_required
def index():
    """Display payroll periods available to the user."""

    periods = PayrollPeriod.query.order_by(
        PayrollPeriod.year.desc(),
        PayrollPeriod.month.desc(),
    ).all()

    return render_template(
        "payroll/index.html",
        periods=periods,
    )


@payroll_bp.route("/period/<int:period_id>")
@login_required
def view_period_payroll(period_id):
    """Display the payroll register for one period."""

    period = PayrollPeriod.query.get_or_404(
        period_id
    )

    records = PayrollService.get_period_records(
        period
    )

    summary = PayrollService.calculate_register_summary(
        records
    )

    form = PayrollProcessForm()

    return render_template(
        "payroll/view_period.html",
        period=period,
        records=records,
        form=form,
        employee_count=summary.employee_count,
        total_basic_salary=(
            summary.total_basic_salary
        ),
        total_gross_pay=summary.total_gross_pay,
        total_deductions=summary.total_deductions,
        total_net_pay=summary.total_net_pay,
    )


@payroll_bp.route(
    "/period/<int:period_id>/process",
    methods=["POST"],
)
@login_required
def process_payroll(period_id):
    """Process active employees into a payroll period."""

    period = PayrollPeriod.query.get_or_404(
        period_id
    )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            "The payroll processing request could not "
            "be validated.",
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    try:
        result = PayrollService.process_period(
            period=period,
            processed_by_user_id=current_user.id,
        )

    except InvalidPayrollStatusError as error:
        flash(
            str(error),
            "warning",
        )

    except NoActiveEmployeesError as error:
        flash(
            str(error),
            "warning",
        )

    except PayrollPersistenceError as error:
        flash(
            str(error),
            "danger",
        )

    else:
        if result.created_count:
            flash(
                f"Payroll records created for "
                f"{result.created_count} employee(s).",
                "success",
            )

        if result.skipped_count:
            flash(
                f"{result.skipped_count} employee(s) were "
                f"skipped because payroll records already "
                f"exist.",
                "info",
            )

        if (
            result.created_count == 0
            and result.skipped_count > 0
        ):
            flash(
                "Payroll was already processed for all "
                "active employees in this period.",
                "info",
            )

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=period.id,
        )
    )


@payroll_bp.route(
    "/record/<int:record_id>/payslip/generate",
    methods=["POST"],
)
@login_required
def generate_payslip(record_id):
    """Generate or regenerate a payroll-record payslip."""

    payroll_record = PayrollRecord.query.get_or_404(
        record_id
    )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            "The payslip generation request could not "
            "be validated.",
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=(
                    payroll_record.payroll_period_id
                ),
            )
        )

    existing_payslip = payroll_record.payslip

    try:
        payslip = PayslipService.generate_payslip(
            payroll_record_id=payroll_record.id,
            generated_by_user_id=current_user.id,
        )

    except PayslipRecordNotFoundError as error:
        flash(
            str(error),
            "warning",
        )

    except PayslipGenerationError as error:
        flash(
            str(error),
            "danger",
        )

    else:
        employee = payroll_record.employee

        employee_name = (
            f"{employee.first_name} "
            f"{employee.last_name}"
        ).strip()

        if existing_payslip is None:
            flash(
                f"Payslip generated successfully for "
                f"{employee_name}.",
                "success",
            )

        else:
            flash(
                f"Payslip regenerated successfully for "
                f"{employee_name}.",
                "success",
            )

        return redirect(
            url_for(
                "payroll.download_payslip",
                payslip_id=payslip.id,
            )
        )

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=(
                payroll_record.payroll_period_id
            ),
        )
    )


@payroll_bp.route(
    "/payslip/<int:payslip_id>/download"
)
@login_required
def download_payslip(payslip_id):
    """Download an existing generated payslip PDF."""

    payslip = Payslip.query.get_or_404(
        payslip_id
    )

    file_path = Path(
        payslip.file_path
    ).resolve()

    if (
        not file_path.exists()
        or not file_path.is_file()
    ):
        flash(
            "The payslip record exists, but the PDF file "
            "could not be found. Please regenerate it.",
            "warning",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=(
                    payslip.payroll_record
                    .payroll_period_id
                ),
            )
        )

    payroll_record = payslip.payroll_record
    employee = payslip.employee
    period = payroll_record.payroll_period

    employee_number = (
        employee.employee_number
        or f"employee_{employee.id}"
    )

    safe_employee_number = (
        str(employee_number)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    download_name = (
        f"BUYOH_Payslip_"
        f"{safe_employee_number}_"
        f"{period.year}_"
        f"{period.month:02d}.pdf"
    )

    return send_file(
        file_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )
