"""Payroll routes."""

from pathlib import Path

from flask import (
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from app.models import PayrollPeriod, PayrollRecord, Payslip
from app.payroll import payroll_bp
from app.payroll.forms import PayrollProcessForm
from app.payroll.workflow_service import PayrollWorkflowError, PayrollWorkflowService
from app.services.bulk_payslip_service import (
    BulkPayslipService,
    BulkPayslipServiceError,
    NoPayrollRecordsError,
)
from app.services.email_service import (
    EmailConfigurationError,
    EmailDeliveryError,
    InvalidEmployeeEmailError,
    MissingEmployeeEmailError,
    PayslipFileNotFoundError,
    EmailService,
)
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
    periods = PayrollPeriod.query.order_by(
        PayrollPeriod.year.desc(),
        PayrollPeriod.month.desc(),
    ).all()
    return render_template("payroll/index.html", periods=periods)


@payroll_bp.route("/period/<int:period_id>")
@login_required
def view_period_payroll(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)
    records = PayrollService.get_period_records(period)
    summary = PayrollService.calculate_register_summary(records)
    form = PayrollProcessForm()
    return render_template(
        "payroll/view_period.html",
        period=period,
        records=records,
        form=form,
        employee_count=summary.employee_count,
        total_basic_salary=summary.total_basic_salary,
        total_gross_pay=summary.total_gross_pay,
        total_deductions=summary.total_deductions,
        total_net_pay=summary.total_net_pay,
    )


@payroll_bp.route("/period/<int:period_id>/process", methods=["POST"])
@login_required
def process_payroll(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)
    try:
        PayrollWorkflowService.ensure_processable(payroll_period=period)
    except PayrollWorkflowError as error:
        flash(str(error), "warning")
        return redirect(url_for("payroll.view_period_payroll", period_id=period.id))

    form = PayrollProcessForm()
    if not form.validate_on_submit():
        flash("The payroll processing request could not be validated.", "danger")
        return redirect(url_for("payroll.view_period_payroll", period_id=period.id))

    try:
        result = PayrollService.process_period(
            period=period,
            processed_by_user_id=current_user.id,
        )
    except InvalidPayrollStatusError as error:
        flash(str(error), "warning")
    except NoActiveEmployeesError as error:
        flash(str(error), "warning")
    except PayrollPersistenceError as error:
        flash(str(error), "danger")
    else:
        if result.created_count:
            flash(
                f"Payroll records created for {result.created_count} employee(s).",
                "success",
            )
        if result.skipped_count:
            flash(
                f"{result.skipped_count} employee(s) were skipped because payroll records already exist.",
                "info",
            )
        if result.created_count == 0 and result.skipped_count > 0:
            flash(
                "Payroll was already processed for all active employees in this period.",
                "info",
            )

    return redirect(url_for("payroll.view_period_payroll", period_id=period.id))


@payroll_bp.route("/period/<int:period_id>/approve", methods=["POST"])
@login_required
def approve_payroll(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)
    form = PayrollProcessForm()
    if not form.validate_on_submit():
        flash("The payroll approval request could not be validated.", "danger")
        return redirect(url_for("payroll.view_period_payroll", period_id=period.id))
    try:
        PayrollWorkflowService.approve_period(
            payroll_period=period,
            user_id=current_user.id,
        )
    except PayrollWorkflowError as error:
        flash(str(error), "warning")
    else:
        flash(f"{period.period_name} payroll was approved successfully.", "success")
    return redirect(url_for("payroll.view_period_payroll", period_id=period.id))


@payroll_bp.route("/period/<int:period_id>/lock", methods=["POST"])
@login_required
def lock_payroll(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)
    form = PayrollProcessForm()
    if not form.validate_on_submit():
        flash("The payroll locking request could not be validated.", "danger")
        return redirect(url_for("payroll.view_period_payroll", period_id=period.id))
    try:
        PayrollWorkflowService.lock_period(
            payroll_period=period,
            user_id=current_user.id,
        )
    except PayrollWorkflowError as error:
        flash(str(error), "warning")
    else:
        flash(f"{period.period_name} payroll was locked successfully.", "success")
    return redirect(url_for("payroll.view_period_payroll", period_id=period.id))


@payroll_bp.route("/period/<int:period_id>/reopen", methods=["POST"])
@login_required
def reopen_payroll(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)
    form = PayrollProcessForm()
    if not form.validate_on_submit():
        flash("The payroll reopening request could not be validated.", "danger")
        return redirect(url_for("payroll.view_period_payroll", period_id=period.id))
    if current_user.role != "Admin":
        flash("Only an administrator can reopen locked payroll.", "danger")
        return redirect(url_for("payroll.view_period_payroll", period_id=period.id))
    try:
        PayrollWorkflowService.reopen_period(
            payroll_period=period,
            user_id=current_user.id,
        )
    except PayrollWorkflowError as error:
        flash(str(error), "warning")
    else:
        flash(f"{period.period_name} payroll was reopened successfully.", "success")
    return redirect(url_for("payroll.view_period_payroll", period_id=period.id))


@payroll_bp.route("/record/<int:record_id>/payslip/generate", methods=["POST"])
@login_required
def generate_payslip(record_id):
    payroll_record = PayrollRecord.query.get_or_404(record_id)
    form = PayrollProcessForm()
    if not form.validate_on_submit():
        flash("The payslip generation request could not be validated.", "danger")
        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=payroll_record.payroll_period_id,
            )
        )

    existing_payslip = payroll_record.payslip
    try:
        payslip = PayslipService.generate_payslip(
            payroll_record_id=payroll_record.id,
            generated_by_user_id=current_user.id,
        )
    except PayslipRecordNotFoundError as error:
        flash(str(error), "warning")
    except PayslipGenerationError as error:
        flash(str(error), "danger")
    else:
        employee = payroll_record.employee
        employee_name = f"{employee.first_name} {employee.last_name}".strip()
        if existing_payslip is None:
            flash(f"Payslip generated successfully for {employee_name}.", "success")
        else:
            flash(f"Payslip regenerated successfully for {employee_name}.", "success")
        return redirect(url_for("payroll.download_payslip", payslip_id=payslip.id))

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=payroll_record.payroll_period_id,
        )
    )



@payroll_bp.route(
    "/period/<int:period_id>/email-payslips",
    methods=["POST"],
)
@login_required
def email_period_payslips(period_id):
    """Email all available payslips for a payroll period."""

    period = PayrollPeriod.query.get_or_404(period_id)
    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            "The bulk payslip email request could not be validated.",
            "danger",
        )
        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    records = PayrollService.get_period_records(period)

    if not records:
        flash(
            "There are no payroll records in this period.",
            "warning",
        )
        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    sent_count = 0
    skipped_no_email = []
    skipped_no_payslip = []
    failed = []

    for record in records:
        employee = record.employee
        employee_name = (
            f"{employee.first_name} {employee.last_name}"
        ).strip()

        if record.payslip is None:
            skipped_no_payslip.append(employee_name)
            continue

        if not employee.email:
            skipped_no_email.append(employee_name)
            continue

        try:
            EmailService.send_payslip(
                payslip=record.payslip,
                sent_by_user_id=current_user.id,
                ip_address=request.remote_addr,
            )

        except (
            MissingEmployeeEmailError,
            InvalidEmployeeEmailError,
            PayslipFileNotFoundError,
            EmailConfigurationError,
            EmailDeliveryError,
        ) as error:
            failed.append(f"{employee_name}: {error}")

        else:
            sent_count += 1

    if sent_count:
        flash(
            f"{sent_count} payslip email(s) sent successfully.",
            "success",
        )

    if skipped_no_email:
        flash(
            "Skipped because no employee email address was saved: "
            + ", ".join(skipped_no_email)
            + ".",
            "warning",
        )

    if skipped_no_payslip:
        flash(
            "Skipped because no payslip had been generated: "
            + ", ".join(skipped_no_payslip)
            + ".",
            "warning",
        )

    if failed:
        flash(
            "Some payslip emails could not be sent: "
            + " | ".join(failed),
            "danger",
        )

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=period.id,
        )
    )


@payroll_bp.route("/period/<int:period_id>/payslips/bulk-download")
@login_required
def download_bulk_payslips(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)
    try:
        result = BulkPayslipService.generate_for_period(payroll_period=period)
    except NoPayrollRecordsError as error:
        flash(str(error), "warning")
        return redirect(url_for("payroll.view_period_payroll", period_id=period.id))
    except BulkPayslipServiceError as error:
        flash(str(error), "danger")
        return redirect(url_for("payroll.view_period_payroll", period_id=period.id))

    download_name = f"BUYOH_All_Payslips_{period.year}_{period.month:02d}.pdf"
    return send_file(
        result.file_path.resolve(),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@payroll_bp.route("/payslip/<int:payslip_id>/download")
@login_required
def download_payslip(payslip_id):
    payslip = Payslip.query.get_or_404(payslip_id)
    file_path = Path(payslip.file_path).resolve()

    if not file_path.exists() or not file_path.is_file():
        flash(
            "The payslip record exists, but the PDF file could not be found. Please regenerate it.",
            "warning",
        )
        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=payslip.payroll_record.payroll_period_id,
            )
        )

    payroll_record = payslip.payroll_record
    employee = payslip.employee
    period = payroll_record.payroll_period
    employee_number = employee.employee_number or f"employee_{employee.id}"
    safe_employee_number = (
        str(employee_number)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )
    download_name = (
        f"BUYOH_Payslip_{safe_employee_number}_{period.year}_{period.month:02d}.pdf"
    )
    return send_file(
        file_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )
