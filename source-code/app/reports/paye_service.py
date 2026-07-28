"""Service layer for PAYE statutory reporting."""

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models import (
    Department,
    Employee,
    PayrollRecord,
)


ZERO = Decimal("0.00")


class PayeReportingService:
    """Provide PAYE and AIDS levy report data."""

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
        Return PAYE report rows and totals.

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
            "taxable_income": ZERO,
            "paye": ZERO,
            "aids_levy": ZERO,
            "total_tax": ZERO,
            "average_paye": ZERO,
            "average_aids_levy": ZERO,
            "average_total_tax": ZERO,
        }

        for record in payroll_records:
            gross_pay = cls._decimal(
                record.gross_pay
            )

            employee_nssa = cls._decimal(
                record.nssa
            )

            paye = cls._decimal(
                record.paye
            )

            aids_levy = cls._decimal(
                record.aids_levy
            )

            taxable_income = (
                gross_pay
                - employee_nssa
            )

            if taxable_income < ZERO:
                taxable_income = ZERO

            total_tax = (
                paye
                + aids_levy
            )

            rows.append(
                {
                    "record": record,
                    "gross_pay": gross_pay,
                    "employee_nssa": employee_nssa,
                    "taxable_income": taxable_income,
                    "paye": paye,
                    "aids_levy": aids_levy,
                    "total_tax": total_tax,
                }
            )

            totals["employee_count"] += 1

            totals["gross_pay"] += (
                gross_pay
            )

            totals["employee_nssa"] += (
                employee_nssa
            )

            totals["taxable_income"] += (
                taxable_income
            )

            totals["paye"] += paye

            totals["aids_levy"] += (
                aids_levy
            )

            totals["total_tax"] += (
                total_tax
            )

        if totals["employee_count"]:
            employee_count = Decimal(
                totals["employee_count"]
            )

            totals["average_paye"] = (
                totals["paye"]
                / employee_count
            )

            totals["average_aids_levy"] = (
                totals["aids_levy"]
                / employee_count
            )

            totals["average_total_tax"] = (
                totals["total_tax"]
                / employee_count
            )

        return {
            "rows": rows,
            "totals": totals,
        }
