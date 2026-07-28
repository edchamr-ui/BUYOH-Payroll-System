"""Routes for payroll reports and analytics."""

from decimal import Decimal

from flask import (
    abort,
    render_template,
    request,
    send_file,
)
from flask_login import (
    current_user,
    login_required,
)
from sqlalchemy import func

from app.extensions import db
from app.models import (
    Department,
    PayrollPeriod,
    PayrollRecord,
)
from app.reports import reports_bp
from app.reports.department_export_service import (
    DepartmentExportService,
)
from app.reports.export_service import ReportExportService
from app.reports.nssa_service import (
    NssaReportingService,
)
from app.reports.services import ReportingService


ZERO = Decimal("0.00")


def _to_decimal(value):
    """Convert a nullable aggregate value to Decimal."""

    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def _get_available_periods():
    """Return payroll periods containing payroll records."""

    return (
        PayrollPeriod.query
        .join(
            PayrollRecord,
            PayrollRecord.payroll_period_id
            == PayrollPeriod.id,
        )
        .distinct()
        .order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc(),
        )
        .all()
    )


def _get_selected_period(
    available_periods,
    requested_period_id=None,
):
    """Resolve a requested period or default to the latest."""

    if requested_period_id:
        selected_period = next(
            (
                period
                for period in available_periods
                if period.id == requested_period_id
            ),
            None,
        )

        if selected_period:
            return selected_period

    if available_periods:
        return available_periods[0]

    return None


def _get_selected_department(
    department_id,
):
    """Return a selected department or None."""

    if not department_id:
        return None

    department = db.session.get(
        Department,
        department_id,
    )

    if department is None:
        abort(404)

    return department


def _get_payroll_summary_context():
    """Resolve filters and payroll-summary report data."""

    available_periods = _get_available_periods()

    requested_period_id = request.args.get(
        "period_id",
        type=int,
    )

    selected_period = _get_selected_period(
        available_periods,
        requested_period_id,
    )

    selected_department_id = request.args.get(
        "department_id",
        type=int,
    )

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    selected_department = _get_selected_department(
        selected_department_id
    )

    if selected_period is None:
        return {
            "available_periods": available_periods,
            "selected_period": None,
            "selected_department_id": (
                selected_department_id
            ),
            "selected_department": (
                selected_department
            ),
            "search_term": search_term,
            "records": [],
            "totals": None,
        }

    report_data = (
        ReportingService.get_payroll_summary(
            period_id=selected_period.id,
            search_term=search_term,
            department_id=selected_department_id,
        )
    )

    return {
        "available_periods": available_periods,
        "selected_period": selected_period,
        "selected_department_id": (
            selected_department_id
        ),
        "selected_department": (
            selected_department
        ),
        "search_term": search_term,
        "records": report_data["records"],
        "totals": report_data["totals"],
    }


def _get_nssa_report_context():
    """Resolve NSSA report filters and data."""

    available_periods = _get_available_periods()

    requested_period_id = request.args.get(
        "period_id",
        type=int,
    )

    selected_period = _get_selected_period(
        available_periods,
        requested_period_id,
    )

    selected_department_id = request.args.get(
        "department_id",
        type=int,
    )

    selected_department = _get_selected_department(
        selected_department_id
    )

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    if selected_period is None:
        return {
            "available_periods": available_periods,
            "selected_period": None,
            "selected_department_id": (
                selected_department_id
            ),
            "selected_department": (
                selected_department
            ),
            "search_term": search_term,
            "rows": [],
            "totals": None,
        }

    report_data = (
        NssaReportingService.get_nssa_report(
            period_id=selected_period.id,
            search_term=search_term,
            department_id=selected_department_id,
        )
    )

    return {
        "available_periods": available_periods,
        "selected_period": selected_period,
        "selected_department_id": (
            selected_department_id
        ),
        "selected_department": (
            selected_department
        ),
        "search_term": search_term,
        "rows": report_data["rows"],
        "totals": report_data["totals"],
    }


@reports_bp.route("/")
@login_required
def index():
    """Display the reports dashboard."""

    available_periods = _get_available_periods()

    requested_period_id = request.args.get(
        "period_id",
        type=int,
    )

    selected_period = _get_selected_period(
        available_periods,
        requested_period_id,
    )

    summary = {
        "employee_count": 0,
        "department_count": 0,
        "basic_salary": ZERO,
        "overtime_amount": ZERO,
        "allowances_total": ZERO,
        "gross_pay": ZERO,
        "employee_nssa": ZERO,
        "employer_nssa": ZERO,
        "paye": ZERO,
        "aids_levy": ZERO,
        "other_deductions": ZERO,
        "total_deductions": ZERO,
        "net_pay": ZERO,
        "employer_cost": ZERO,
    }

    if selected_period:
        totals = (
            db.session.query(
                func.count(
                    PayrollRecord.id
                ).label("employee_count"),
                func.count(
                    func.distinct(
                        Department.id
                    )
                ).label("department_count"),
                func.sum(
                    PayrollRecord.basic_salary
                ).label("basic_salary"),
                func.sum(
                    PayrollRecord.overtime_amount
                ).label("overtime_amount"),
                func.sum(
                    PayrollRecord.allowances_total
                ).label("allowances_total"),
                func.sum(
                    PayrollRecord.gross_pay
                ).label("gross_pay"),
                func.sum(
                    PayrollRecord.nssa
                ).label("employee_nssa"),
                func.sum(
                    PayrollRecord.employer_nssa
                ).label("employer_nssa"),
                func.sum(
                    PayrollRecord.paye
                ).label("paye"),
                func.sum(
                    PayrollRecord.aids_levy
                ).label("aids_levy"),
                func.sum(
                    PayrollRecord.other_deductions_total
                ).label("other_deductions"),
                func.sum(
                    PayrollRecord.total_deductions
                ).label("total_deductions"),
                func.sum(
                    PayrollRecord.net_pay
                ).label("net_pay"),
                func.sum(
                    PayrollRecord.employer_cost
                ).label("employer_cost"),
            )
            .join(
                PayrollRecord.employee
            )
            .join(
                Department
            )
            .filter(
                PayrollRecord.payroll_period_id
                == selected_period.id
            )
            .one()
        )

        summary = {
            "employee_count": (
                totals.employee_count or 0
            ),
            "department_count": (
                totals.department_count or 0
            ),
            "basic_salary": _to_decimal(
                totals.basic_salary
            ),
            "overtime_amount": _to_decimal(
                totals.overtime_amount
            ),
            "allowances_total": _to_decimal(
                totals.allowances_total
            ),
            "gross_pay": _to_decimal(
                totals.gross_pay
            ),
            "employee_nssa": _to_decimal(
                totals.employee_nssa
            ),
            "employer_nssa": _to_decimal(
                totals.employer_nssa
            ),
            "paye": _to_decimal(
                totals.paye
            ),
            "aids_levy": _to_decimal(
                totals.aids_levy
            ),
            "other_deductions": _to_decimal(
                totals.other_deductions
            ),
            "total_deductions": _to_decimal(
                totals.total_deductions
            ),
            "net_pay": _to_decimal(
                totals.net_pay
            ),
            "employer_cost": _to_decimal(
                totals.employer_cost
            ),
        }

    total_tax = (
        summary["paye"]
        + summary["aids_levy"]
    )

    total_nssa = (
        summary["employee_nssa"]
        + summary["employer_nssa"]
    )

    return render_template(
        "reports/index.html",
        available_periods=available_periods,
        selected_period=selected_period,
        summary=summary,
        total_tax=total_tax,
        total_nssa=total_nssa,
    )


@reports_bp.route("/payroll-summary")
@login_required
def payroll_summary():
    """Display the detailed payroll summary report."""

    context = _get_payroll_summary_context()

    departments = (
        Department.query
        .filter_by(
            is_active=True
        )
        .order_by(
            Department.name.asc()
        )
        .all()
    )

    return render_template(
        "reports/payroll_summary.html",
        departments=departments,
        **context,
    )


@reports_bp.route("/payroll-summary/pdf")
@login_required
def payroll_summary_pdf():
    """Download the payroll summary as a PDF."""

    context = _get_payroll_summary_context()

    selected_period = context[
        "selected_period"
    ]

    if selected_period is None:
        abort(404)

    pdf_buffer = (
        ReportExportService
        .generate_payroll_summary_pdf(
            selected_period=selected_period,
            records=context["records"],
            totals=context["totals"],
            generated_by=current_user,
            search_term=context["search_term"],
            selected_department=context[
                "selected_department"
            ],
        )
    )

    filename = (
        "payroll-summary-"
        f"{selected_period.year}-"
        f"{selected_period.month:02d}.pdf"
    )

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


@reports_bp.route("/payroll-summary/excel")
@login_required
def payroll_summary_excel():
    """Download the payroll summary as an Excel workbook."""

    context = _get_payroll_summary_context()

    selected_period = context[
        "selected_period"
    ]

    if selected_period is None:
        abort(404)

    excel_buffer = (
        ReportExportService
        .generate_payroll_summary_excel(
            selected_period=selected_period,
            records=context["records"],
            totals=context["totals"],
            generated_by=current_user,
            search_term=context["search_term"],
            selected_department=context[
                "selected_department"
            ],
        )
    )

    filename = (
        "payroll-summary-"
        f"{selected_period.year}-"
        f"{selected_period.month:02d}.xlsx"
    )

    return send_file(
        excel_buffer,
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


@reports_bp.route("/department-summary")
@login_required
def department_summary():
    """Display payroll costs grouped by department."""

    available_periods = _get_available_periods()

    requested_period_id = request.args.get(
        "period_id",
        type=int,
    )

    selected_period = _get_selected_period(
        available_periods,
        requested_period_id,
    )

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    if selected_period is None:
        return render_template(
            "reports/department_summary.html",
            available_periods=[],
            selected_period=None,
            search_term=search_term,
            departments=[],
            totals=None,
        )

    report_data = (
        ReportingService.get_department_summary(
            period_id=selected_period.id,
            search_term=search_term,
        )
    )

    return render_template(
        "reports/department_summary.html",
        available_periods=available_periods,
        selected_period=selected_period,
        search_term=search_term,
        departments=report_data["departments"],
        totals=report_data["totals"],
    )


@reports_bp.route("/department-summary/pdf")
@login_required
def department_summary_pdf():
    """Download the Department Summary PDF."""

    available_periods = _get_available_periods()

    requested_period_id = request.args.get(
        "period_id",
        type=int,
    )

    selected_period = _get_selected_period(
        available_periods,
        requested_period_id,
    )

    if selected_period is None:
        abort(404)

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    report_data = (
        ReportingService.get_department_summary(
            period_id=selected_period.id,
            search_term=search_term,
        )
    )

    pdf_buffer = (
        DepartmentExportService
        .generate_department_summary_pdf(
            selected_period=selected_period,
            departments=report_data[
                "departments"
            ],
            totals=report_data["totals"],
            generated_by=current_user,
            search_term=search_term,
        )
    )

    filename = (
        "department-summary-"
        f"{selected_period.year}-"
        f"{selected_period.month:02d}.pdf"
    )

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


@reports_bp.route("/department-summary/excel")
@login_required
def department_summary_excel():
    """Download the Department Summary Excel workbook."""

    available_periods = _get_available_periods()

    requested_period_id = request.args.get(
        "period_id",
        type=int,
    )

    selected_period = _get_selected_period(
        available_periods,
        requested_period_id,
    )

    if selected_period is None:
        abort(404)

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    report_data = (
        ReportingService.get_department_summary(
            period_id=selected_period.id,
            search_term=search_term,
        )
    )

    excel_buffer = (
        DepartmentExportService
        .generate_department_summary_excel(
            selected_period=selected_period,
            departments=report_data[
                "departments"
            ],
            totals=report_data["totals"],
            generated_by=current_user,
            search_term=search_term,
        )
    )

    filename = (
        "department-summary-"
        f"{selected_period.year}-"
        f"{selected_period.month:02d}.xlsx"
    )

    return send_file(
        excel_buffer,
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


@reports_bp.route("/nssa")
@login_required
def nssa_report():
    """Display the NSSA statutory report."""

    context = _get_nssa_report_context()

    departments = (
        Department.query
        .filter_by(
            is_active=True
        )
        .order_by(
            Department.name.asc()
        )
        .all()
    )

    return render_template(
        "reports/nssa_report.html",
        departments=departments,
        **context,
    )
