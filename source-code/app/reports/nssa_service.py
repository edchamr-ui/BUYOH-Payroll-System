"""Service layer for NSSA statutory reporting."""

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models import (
    Department,
    Employee,
    PayrollRecord,
)


ZERO = Decimal("0.00")


class NssaReportingService:
    """Provide NSSA statutory report data."""

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
        Return NSSA contribution rows and totals.

        Filters:
        - payroll period,
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
                PayrollRecord.payroll_period_id == period_id
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
                Employee.last_name.asc(),
                Employee.first_name.asc(),
                Employee.employee_number.asc(),
            )
            .all()
        )

        rows = []

        totals = {
            "employee_count": 0,
            "gross_pay": ZERO,
            "employee_nssa": ZERO,
            "employer_nssa": ZERO,
            "total_nssa": ZERO,
            "average_employee_nssa": ZERO,
            "average_employer_nssa": ZERO,
            "average_total_nssa": ZERO,
        }

        for record in payroll_records:
            employee_nssa = cls._decimal(
                record.nssa
            )

            employer_nssa = cls._decimal(
                record.employer_nssa
            )

            gross_pay = cls._decimal(
                record.gross_pay
            )

            total_nssa = (
                employee_nssa
                + employer_nssa
            )

            rows.append(
                {
                    "record": record,
                    "gross_pay": gross_pay,
                    "employee_nssa": employee_nssa,
                    "employer_nssa": employer_nssa,
                    "total_nssa": total_nssa,
                }
            )

            totals["employee_count"] += 1
            totals["gross_pay"] += gross_pay
            totals["employee_nssa"] += employee_nssa
            totals["employer_nssa"] += employer_nssa
            totals["total_nssa"] += total_nssa

        if totals["employee_count"]:
            employee_count = Decimal(
                totals["employee_count"]
            )

            totals["average_employee_nssa"] = (
                totals["employee_nssa"]
                / employee_count
            )

            totals["average_employer_nssa"] = (
                totals["employer_nssa"]
                / employee_count
            )

            totals["average_total_nssa"] = (
                totals["total_nssa"]
                / employee_count
            )

        return {
            "rows": rows,
            "totals": totals,
        }
