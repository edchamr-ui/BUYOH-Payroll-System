"""Routes for viewing and managing generated payslips."""

from flask import (
    render_template,
    request,
)
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models import (
    Employee,
    PayrollPeriod,
    PayrollRecord,
    Payslip,
)
from app.payroll.forms import PayrollProcessForm
from app.payslips import payslips_bp


@payslips_bp.route("/")
@login_required
def index():
    """Display all generated payslips."""

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    selected_period_id = request.args.get(
        "period_id",
        type=int,
    )

    query = (
        Payslip.query
        .join(
            Employee,
            Payslip.employee_id == Employee.id,
        )
        .join(
            PayrollRecord,
            Payslip.payroll_record_id
            == PayrollRecord.id,
        )
        .join(
            PayrollPeriod,
            PayrollRecord.payroll_period_id
            == PayrollPeriod.id,
        )
        .options(
            joinedload(Payslip.employee).joinedload(
                Employee.department
            ),
            joinedload(Payslip.generator),
            joinedload(Payslip.payroll_record).joinedload(
                PayrollRecord.payroll_period
            ),
        )
    )

    if search_term:
        search_pattern = f"%{search_term}%"

        query = query.filter(
            or_(
                Employee.employee_number.ilike(
                    search_pattern
                ),
                Employee.first_name.ilike(
                    search_pattern
                ),
                Employee.last_name.ilike(
                    search_pattern
                ),
            )
        )

    if selected_period_id:
        query = query.filter(
            PayrollPeriod.id == selected_period_id
        )

    payslips = query.order_by(
        Payslip.generated_at.desc(),
        Payslip.id.desc(),
    ).all()

    available_periods = (
        PayrollPeriod.query
        .join(
            PayrollRecord,
            PayrollRecord.payroll_period_id
            == PayrollPeriod.id,
        )
        .join(
            Payslip,
            Payslip.payroll_record_id
            == PayrollRecord.id,
        )
        .distinct()
        .order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc(),
        )
        .all()
    )

    form = PayrollProcessForm()

    total_payslips = Payslip.query.count()

    return render_template(
        "payslips/index.html",
        payslips=payslips,
        available_periods=available_periods,
        selected_period_id=selected_period_id,
        search_term=search_term,
        total_payslips=total_payslips,
        displayed_count=len(payslips),
        form=form,
    )
