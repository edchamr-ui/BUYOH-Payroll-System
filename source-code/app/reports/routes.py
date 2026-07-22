"""Routes for payroll reports and analytics."""

from decimal import Decimal

from flask import render_template, request
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import (
    Department,
    PayrollPeriod,
    PayrollRecord,
)
from app.reports import reports_bp


ZERO = Decimal("0.00")


def _to_decimal(value):
    """Convert a nullable aggregate value to Decimal."""

    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


@reports_bp.route("/")
@login_required
def index():
    """Display the reports dashboard."""

    available_periods = (
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

    requested_period_id = request.args.get(
        "period_id",
        type=int,
    )

    selected_period = None

    if requested_period_id:
        selected_period = next(
            (
                period
                for period in available_periods
                if period.id == requested_period_id
            ),
            None,
        )

    if selected_period is None and available_periods:
        selected_period = available_periods[0]

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
                PayrollRecord.employee,
            )
            .join(
                Department,
            )
            .filter(
                PayrollRecord.payroll_period_id
                == selected_period.id,
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
