"""Service layer for the Cash Payment Register."""

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models import (
    Department,
    Employee,
    PayrollRecord,
)


ZERO = Decimal("0.00")


class CashPaymentReportingService:
    """Provide cash-payment register data."""

    @staticmethod
    def _decimal(value):
        """Convert a nullable numeric value to Decimal."""

        if value is None:
            return ZERO

        if isinstance(value, Decimal):
            return value

        return Decimal(str(value))

    @classmethod
    def get_report(
        cls,
        period_id,
        search_term="",
        department_id=None,
    ):
        """
        Return cash-payment register rows and totals.

        Filters:
        - payroll period,
        - employees paid by cash,
        - employee name or employee number,
        - department.
        """

        query = (
            PayrollRecord.query
            .join(
                Employee,
                PayrollRecord.employee_id == Employee.id,
            )
            .join(
                Department,
                Employee.department_id == Department.id,
            )
            .options(
                joinedload(
                    PayrollRecord.employee
                ).joinedload(
                    Employee.department
                ),
                joinedload(
                    PayrollRecord.payroll_period
                ),
            )
            .filter(
                PayrollRecord.payroll_period_id == period_id,
                Employee.payment_method == "Cash",
            )
        )

        search_term = search_term.strip()

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
                    (
                        Employee.first_name
                        + " "
                        + Employee.last_name
                    ).ilike(
                        search_pattern
                    ),
                )
            )

        if department_id:
            query = query.filter(
                Employee.department_id == department_id
            )

        payroll_records = (
            query
            .order_by(
                Department.name.asc(),
                Employee.last_name.asc(),
                Employee.first_name.asc(),
                Employee.employee_number.asc(),
            )
            .all()
        )

        rows = []

        totals = {
            "employee_count": 0,
            "department_count": 0,
            "gross_pay": ZERO,
            "total_deductions": ZERO,
            "total_cash": ZERO,
            "average_cash_payment": ZERO,
        }

        department_ids = set()

        for record in payroll_records:
            gross_pay = cls._decimal(
                record.gross_pay
            )

            total_deductions = cls._decimal(
                record.total_deductions
            )

            net_pay = cls._decimal(
                record.net_pay
            )

            employee = record.employee
            department = employee.department

            rows.append(
                {
                    "record": record,
                    "employee": employee,
                    "department": department,
                    "gross_pay": gross_pay,
                    "total_deductions": total_deductions,
                    "net_pay": net_pay,
                }
            )

            totals["employee_count"] += 1
            totals["gross_pay"] += gross_pay
            totals["total_deductions"] += (
                total_deductions
            )
            totals["total_cash"] += net_pay

            if employee.department_id is not None:
                department_ids.add(
                    employee.department_id
                )

        totals["department_count"] = len(
            department_ids
        )

        if totals["employee_count"]:
            employee_count = Decimal(
                totals["employee_count"]
            )

            totals["average_cash_payment"] = (
                totals["total_cash"]
                / employee_count
            )

        return {
            "rows": rows,
            "totals": totals,
        }

