"""Payroll routes."""

import calendar
from pathlib import Path

from flask import (
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)
from sqlalchemy import or_

from app.models import (
    PayrollPeriod,
    PayrollRecord,
    Payslip,
)
from app.payroll import payroll_bp
from app.payroll.forms import PayrollProcessForm
from app.payroll.workflow_service import (
    PayrollWorkflowError,
    PayrollWorkflowService,
)
from app.services.bulk_payslip_service import (
    BulkPayslipService,
    BulkPayslipServiceError,
    NoPayrollRecordsError,
)
from app.services.company_settings_service import (
    CompanySettingsService,
)
from app.services.email_service import (
    EmailConfigurationError,
    EmailDeliveryError,
    EmailService,
    InvalidEmployeeEmailError,
    MissingEmployeeEmailError,
    PayslipFileNotFoundError,
)
from app.services.payroll_service import (
    InvalidPayrollStatusError,
    NoActiveEmployeesError,
    PayrollConfigurationError,
    PayrollPersistenceError,
    PayrollService,
)
from app.services.payslip_service import (
    PayslipGenerationError,
    PayslipRecordNotFoundError,
    PayslipService,
)
from app.services.period_payslip_service import (
    EmptyPayrollRegisterError,
    InvalidPeriodPayslipStatusError,
    PeriodPayslipService,
)


def _safe_filename_part(value, fallback="payroll"):
    """Return a filesystem-safe filename component."""

    text = str(value or "").strip()

    if not text:
        text = fallback

    for character in (
        "/",
        "\\",
        ":",
        "*",
        "?",
        '"',
        "<",
        ">",
        "|",
    ):
        text = text.replace(
            character,
            "_",
        )

    text = "_".join(
        text.split()
    )

    return text


def _company_filename_name():
    """Return a configured company name for downloaded files."""

    profile = (
        CompanySettingsService.get_company_profile()
    )

    return _safe_filename_part(
        profile.get("display_name")
        or profile.get("trading_name")
        or profile.get("company_name")
        or "Company"
    )


@payroll_bp.route("/")
@login_required
def index():
    """Display searchable payroll periods with operational summaries."""

    search_term = request.args.get("q", "").strip()
    year_filter = request.args.get("year", "").strip()
    status_filter = request.args.get("status", "all").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 12

    query = PayrollPeriod.query

    if search_term:
        search_conditions = []

        if search_term.isdigit():
            numeric_value = int(search_term)
            search_conditions.append(
                PayrollPeriod.year == numeric_value
            )

            if 1 <= numeric_value <= 12:
                search_conditions.append(
                    PayrollPeriod.month == numeric_value
                )

        matching_months = [
            month_number
            for month_number in range(1, 13)
            if search_term.lower()
            in calendar.month_name[month_number].lower()
        ]

        if matching_months:
            search_conditions.append(
                PayrollPeriod.month.in_(matching_months)
            )

        if search_conditions:
            query = query.filter(or_(*search_conditions))
        else:
            query = query.filter(PayrollPeriod.id == -1)

    if year_filter:
        try:
            selected_year = int(year_filter)
        except ValueError:
            selected_year = None

        if selected_year is not None:
            query = query.filter(
                PayrollPeriod.year == selected_year
            )

    if status_filter != "all":
        query = query.filter(
            PayrollPeriod.status == status_filter
        )

    available_years = [
        year
        for (year,) in (
            PayrollPeriod.query
            .with_entities(PayrollPeriod.year)
            .distinct()
            .order_by(PayrollPeriod.year.desc())
            .all()
        )
    ]

    available_statuses = [
        status
        for (status,) in (
            PayrollPeriod.query
            .with_entities(PayrollPeriod.status)
            .distinct()
            .order_by(PayrollPeriod.status.asc())
            .all()
        )
        if status
    ]

    pagination = (
        query
        .order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc(),
        )
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )
    )

    period_rows = []

    for period in pagination.items:
        records = PayrollService.get_period_records(period)
        summary = PayrollService.calculate_register_summary(
            records
        )

        period_rows.append(
            {
                "period": period,
                "employee_count": summary.employee_count,
                "gross_payroll": summary.total_gross_pay,
                "net_payroll": summary.total_net_pay,
                "payslip_count": sum(
                    1
                    for record in records
                    if record.payslip is not None
                ),
            }
        )

    company_profile = (
        CompanySettingsService.get_company_profile()
    )

    currency_code = (
        company_profile.get("currency_code")
        or company_profile.get("currency")
        or ""
    )

    return render_template(
        "payroll/index.html",
        period_rows=period_rows,
        pagination=pagination,
        search_term=search_term,
        year_filter=year_filter,
        status_filter=status_filter,
        available_years=available_years,
        available_statuses=available_statuses,
        currency_code=currency_code,
    )


@payroll_bp.route(
    "/period/<int:period_id>"
)
@login_required
def view_period_payroll(
    period_id,
):
    """Display one payroll register."""

    period = (
        PayrollPeriod.query
        .get_or_404(
            period_id
        )
    )

    records = (
        PayrollService.get_period_records(
            period
        )
    )

    summary = (
        PayrollService
        .calculate_register_summary(
            records
        )
    )

    generated_payslip_count = sum(
        1
        for record in records
        if record.payslip is not None
    )

    missing_payslip_count = (
        len(records)
        - generated_payslip_count
    )

    form = PayrollProcessForm()

    return render_template(
        "payroll/view_period.html",
        period=period,
        records=records,
        form=form,
        employee_count=(
            summary.employee_count
        ),
        total_basic_salary=(
            summary.total_basic_salary
        ),
        total_gross_pay=(
            summary.total_gross_pay
        ),
        total_deductions=(
            summary.total_deductions
        ),
        total_net_pay=(
            summary.total_net_pay
        ),
        generated_payslip_count=(
            generated_payslip_count
        ),
        missing_payslip_count=(
            missing_payslip_count
        ),
    )


@payroll_bp.route(
    "/period/<int:period_id>/process",
    methods=["POST"],
)
@login_required
def process_payroll(
    period_id,
):
    """Process payroll for active employees."""

    period = (
        PayrollPeriod.query
        .get_or_404(
            period_id
        )
    )

    try:
        PayrollWorkflowService.ensure_processable(
            payroll_period=period
        )

    except PayrollWorkflowError as error:
        flash(
            str(error),
            "warning",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            (
                "The payroll processing request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    try:
        result = (
            PayrollService.process_period(
                period=period,
                processed_by_user_id=(
                    current_user.id
                ),
            )
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

    except PayrollConfigurationError as error:
        flash(
            str(error),
            "danger",
        )

    except PayrollPersistenceError as error:
        flash(
            str(error),
            "danger",
        )

    else:
        if result.provisional_rule_used:
            effective_to = (
                result.rule_effective_to.isoformat()
                if result.rule_effective_to is not None
                else "its configured end date"
            )
            flash(
                (
                    f"Provisional statutory fallback used: "
                    f"{result.rule_set_name}, valid through "
                    f"{effective_to}. Review and recalculate this "
                    "payroll when confirmed current-year ZIMRA "
                    "USD PAYE tables become available."
                ),
                "warning",
            )

        if result.created_count:
            flash(
                (
                    "Payroll records created for "
                    f"{result.created_count} "
                    "employee(s)."
                ),
                "success",
            )

        if result.skipped_count:
            flash(
                (
                    f"{result.skipped_count} employee(s) "
                    "were skipped because payroll "
                    "records already exist."
                ),
                "info",
            )

        if (
            result.created_count == 0
            and result.skipped_count > 0
        ):
            flash(
                (
                    "Payroll was already processed for "
                    "all active employees in this period."
                ),
                "info",
            )

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=period.id,
        )
    )


@payroll_bp.route(
    "/period/<int:period_id>/approve",
    methods=["POST"],
)
@login_required
def approve_payroll(
    period_id,
):
    """Approve a processed payroll period."""

    period = (
        PayrollPeriod.query
        .get_or_404(
            period_id
        )
    )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            (
                "The payroll approval request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    try:
        PayrollWorkflowService.approve_period(
            payroll_period=period,
            user_id=current_user.id,
        )

    except PayrollWorkflowError as error:
        flash(
            str(error),
            "warning",
        )

    else:
        flash(
            (
                f"{period.period_name} payroll "
                "was approved successfully."
            ),
            "success",
        )

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=period.id,
        )
    )


@payroll_bp.route(
    "/period/<int:period_id>/lock",
    methods=["POST"],
)
@login_required
def lock_payroll(
    period_id,
):
    """Lock an approved payroll period."""

    period = (
        PayrollPeriod.query
        .get_or_404(
            period_id
        )
    )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            (
                "The payroll locking request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    try:
        PayrollWorkflowService.lock_period(
            payroll_period=period,
            user_id=current_user.id,
        )

    except PayrollWorkflowError as error:
        flash(
            str(error),
            "warning",
        )

    else:
        flash(
            (
                f"{period.period_name} payroll "
                "was locked successfully."
            ),
            "success",
        )

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=period.id,
        )
    )


@payroll_bp.route(
    "/period/<int:period_id>/reopen",
    methods=["POST"],
)
@login_required
def reopen_payroll(
    period_id,
):
    """Reopen a locked payroll period."""

    period = (
        PayrollPeriod.query
        .get_or_404(
            period_id
        )
    )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            (
                "The payroll reopening request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    if current_user.role != "Admin":
        flash(
            (
                "Only an administrator can reopen "
                "locked payroll."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    try:
        PayrollWorkflowService.reopen_period(
            payroll_period=period,
            user_id=current_user.id,
        )

    except PayrollWorkflowError as error:
        flash(
            str(error),
            "warning",
        )

    else:
        flash(
            (
                f"{period.period_name} payroll "
                "was reopened successfully."
            ),
            "success",
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
def generate_payslip(
    record_id,
):
    """Generate or regenerate one employee payslip."""

    payroll_record = (
        PayrollRecord.query
        .get_or_404(
            record_id
        )
    )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            (
                "The payslip generation request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=(
                    payroll_record
                    .payroll_period_id
                ),
            )
        )

    existing_payslip = (
        payroll_record.payslip
    )

    try:
        payslip = (
            PayslipService.generate_payslip(
                payroll_record_id=(
                    payroll_record.id
                ),
                generated_by_user_id=(
                    current_user.id
                ),
            )
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
                (
                    "Payslip generated successfully "
                    f"for {employee_name}."
                ),
                "success",
            )

        else:
            flash(
                (
                    "Payslip regenerated successfully "
                    f"for {employee_name}."
                ),
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
                payroll_record
                .payroll_period_id
            ),
        )
    )


@payroll_bp.route(
    (
        "/period/<int:period_id>/"
        "payslips/generate-missing"
    ),
    methods=["POST"],
)
@login_required
def generate_missing_payslips(
    period_id,
):
    """Generate missing individual payslips for a period."""

    period = (
        PayrollPeriod.query
        .get_or_404(
            period_id
        )
    )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            (
                "The payslip generation request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    try:
        result = (
            PeriodPayslipService.generate_missing(
                payroll_period=period,
                generated_by_user_id=(
                    current_user.id
                ),
            )
        )

    except (
        InvalidPeriodPayslipStatusError,
        EmptyPayrollRegisterError,
    ) as error:
        flash(
            str(error),
            "warning",
        )

    else:
        if result.generated_count:
            flash(
                (
                    f"{result.generated_count} missing "
                    "individual payslip(s) generated "
                    f"successfully for "
                    f"{period.period_name}."
                ),
                "success",
            )

        if result.skipped_count:
            flash(
                (
                    f"{result.skipped_count} existing "
                    "payslip(s) were left unchanged."
                ),
                "info",
            )

        if result.failed_count:
            failed_names = ", ".join(
                failure.employee_name
                for failure
                in result.failures[:5]
            )

            flash(
                (
                    f"{result.failed_count} payslip(s) "
                    "could not be generated. "
                    "Affected employees: "
                    f"{failed_names}."
                ),
                "danger",
            )

        if (
            result.generated_count == 0
            and result.failed_count == 0
        ):
            flash(
                (
                    "All individual payslips for this "
                    "payroll period have already "
                    "been generated."
                ),
                "info",
            )

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=period.id,
        )
    )


@payroll_bp.route(
    "/period/<int:period_id>/email-payslips",
    methods=["POST"],
)
@login_required
def email_period_payslips(
    period_id,
):
    """Email all generated payslips for a payroll period."""

    period = (
        PayrollPeriod.query
        .get_or_404(
            period_id
        )
    )

    form = PayrollProcessForm()

    if not form.validate_on_submit():
        flash(
            (
                "The bulk payslip email request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    records = (
        PayrollService.get_period_records(
            period
        )
    )

    if not records:
        flash(
            (
                "There are no payroll records "
                "in this period."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    sent_count = 0
    skipped_no_payslip = []
    failed = []

    for record in records:
        employee = record.employee

        employee_name = (
            f"{employee.first_name} "
            f"{employee.last_name}"
        ).strip()

        if record.payslip is None:
            skipped_no_payslip.append(
                employee_name
            )

            continue

        try:
            EmailService.send_payslip(
                payslip=record.payslip,
                sent_by_user_id=(
                    current_user.id
                ),
                ip_address=request.remote_addr,
            )

        except (
            MissingEmployeeEmailError,
            InvalidEmployeeEmailError,
            PayslipFileNotFoundError,
            EmailConfigurationError,
            EmailDeliveryError,
        ) as error:
            failed.append(
                f"{employee_name}: {error}"
            )

        else:
            sent_count += 1

    if sent_count:
        flash(
            (
                f"{sent_count} payslip email(s) "
                "sent successfully."
            ),
            "success",
        )

    if skipped_no_payslip:
        flash(
            (
                "Skipped because no payslip had "
                "been generated: "
                + ", ".join(
                    skipped_no_payslip
                )
                + "."
            ),
            "warning",
        )

    if failed:
        flash(
            (
                "Some payslip emails could not "
                "be sent: "
                + " | ".join(
                    failed
                )
            ),
            "danger",
        )

    if (
        not sent_count
        and not skipped_no_payslip
        and not failed
    ):
        flash(
            (
                "No payslip emails were "
                "processed."
            ),
            "info",
        )

    return redirect(
        url_for(
            "payroll.view_period_payroll",
            period_id=period.id,
        )
    )


@payroll_bp.route(
    (
        "/period/<int:period_id>/"
        "payslips/bulk-download"
    )
)
@login_required
def download_bulk_payslips(
    period_id,
):
    """Generate and download the printable payslip book."""

    period = (
        PayrollPeriod.query
        .get_or_404(
            period_id
        )
    )

    try:
        result = (
            BulkPayslipService
            .generate_for_period(
                payroll_period=period
            )
        )

    except NoPayrollRecordsError as error:
        flash(
            str(error),
            "warning",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    except BulkPayslipServiceError as error:
        flash(
            str(error),
            "danger",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=period.id,
            )
        )

    company_name = (
        _company_filename_name()
    )

    download_name = (
        f"{company_name}_All_Payslips_"
        f"{period.year}_"
        f"{period.month:02d}.pdf"
    )

    return send_file(
        result.file_path.resolve(),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@payroll_bp.route(
    "/payslip/<int:payslip_id>/download"
)
@login_required
def download_payslip(
    payslip_id,
):
    """Download an individual generated payslip."""

    payslip = (
        Payslip.query
        .get_or_404(
            payslip_id
        )
    )

    file_path = Path(
        payslip.file_path
    ).resolve()

    if (
        not file_path.exists()
        or not file_path.is_file()
    ):
        flash(
            (
                "The payslip record exists, but the "
                "PDF file could not be found. "
                "Please regenerate it."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "payroll.view_period_payroll",
                period_id=(
                    payslip
                    .payroll_record
                    .payroll_period_id
                ),
            )
        )

    payroll_record = (
        payslip.payroll_record
    )

    employee = payslip.employee

    period = (
        payroll_record.payroll_period
    )

    employee_number = (
        employee.employee_number
        or f"employee_{employee.id}"
    )

    safe_employee_number = (
        _safe_filename_part(
            employee_number,
            fallback=(
                f"employee_{employee.id}"
            ),
        )
    )

    company_name = (
        _company_filename_name()
    )

    download_name = (
        f"{company_name}_Payslip_"
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
