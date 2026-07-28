"""Service layer for the Bank Transfer Schedule."""

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models import (
    Department,
    Employee,
    PayrollRecord,
)


ZERO = Decimal("0.00")


class BankTransferReportingService:
    """Provide bank-transfer schedule data."""

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
        Return bank-transfer rows and totals.

        Filters:
        - payroll period,
        - employees paid by bank transfer,
        - employee name or employee number,
        - bank name,
        - account number,
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
                Employee.payment_method == "Bank Transfer",
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
                    Employee.bank_name.ilike(
                        search_pattern
                    ),
                    Employee.account_name.ilike(
                        search_pattern
                    ),
                    Employee.account_number.ilike(
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
                Employee.bank_name.asc(),
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
            "bank_count": 0,
            "gross_pay": ZERO,
            "total_deductions": ZERO,
            "total_transfer": ZERO,
            "average_transfer": ZERO,
        }

        department_ids = set()
        bank_names = set()

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
                    "bank_name": employee.bank_name or "",
                    "bank_branch": employee.bank_branch or "",
                    "bank_code": employee.bank_code or "",
                    "account_name": employee.account_name or "",
                    "account_number": employee.account_number or "",
                    "account_type": employee.account_type or "",
                }
            )

            totals["employee_count"] += 1
            totals["gross_pay"] += gross_pay
            totals["total_deductions"] += (
                total_deductions
            )
            totals["total_transfer"] += net_pay

            if employee.department_id is not None:
                department_ids.add(
                    employee.department_id
                )

            if employee.bank_name:
                bank_names.add(
                    employee.bank_name.strip().lower()
                )

        totals["department_count"] = len(
            department_ids
        )

        totals["bank_count"] = len(
            bank_names
        )

        if totals["employee_count"]:
            employee_count = Decimal(
                totals["employee_count"]
            )

            totals["average_transfer"] = (
                totals["total_transfer"]
                / employee_count
            )

        return {
            "rows": rows,
            "totals": totals,
        }
