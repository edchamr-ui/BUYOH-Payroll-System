"""Reusable services for payroll reporting."""

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models import (
    Department,
    Employee,
    PayrollRecord,
)


ZERO = Decimal("0.00")


class ReportingService:
    """Provide reusable payroll reporting queries and calculations."""

    @staticmethod
    def _decimal(value):
        """Return a safe Decimal value."""

        if value is None:
            return ZERO

        if isinstance(value, Decimal):
            return value

        return Decimal(str(value))

    @classmethod
    def get_payroll_summary(
        cls,
        period_id,
        search_term="",
        department_id=None,
    ):
        """
        Return payroll-summary records and calculated totals.

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

        records = (
            query
            .order_by(
                Employee.last_name.asc(),
                Employee.first_name.asc(),
                Employee.employee_number.asc(),
            )
            .all()
        )

        totals = {
            "employee_count": len(records),
            "basic_salary": ZERO,
            "overtime_amount": ZERO,
            "allowances_total": ZERO,
            "gross_pay": ZERO,
            "statutory_sick_pay": ZERO,
            "ssp_salary_withheld": ZERO,
            "statutory_maternity_pay": ZERO,
            "smp_salary_withheld": ZERO,
            "employee_nssa": ZERO,
            "employer_nssa": ZERO,
            "paye": ZERO,
            "aids_levy": ZERO,
            "other_deductions": ZERO,
            "total_deductions": ZERO,
            "net_pay": ZERO,
            "employer_cost": ZERO,
        }

        for record in records:
            totals["basic_salary"] += cls._decimal(
                record.basic_salary
            )

            totals["overtime_amount"] += cls._decimal(
                record.overtime_amount
            )

            totals["allowances_total"] += cls._decimal(
                record.allowances_total
            )

            totals["gross_pay"] += cls._decimal(
                record.gross_pay
            )

            totals["statutory_sick_pay"] += cls._decimal(
                getattr(record, "uk_ssp_amount", ZERO)
            )

            totals["ssp_salary_withheld"] += cls._decimal(
                getattr(record, "uk_ssp_salary_withheld", ZERO)
            )

            totals["statutory_maternity_pay"] += cls._decimal(
                getattr(record, "uk_smp_amount", ZERO)
            )

            totals["smp_salary_withheld"] += cls._decimal(
                getattr(record, "uk_smp_salary_withheld", ZERO)
            )

            totals["employee_nssa"] += cls._decimal(
                record.nssa
            )

            totals["employer_nssa"] += cls._decimal(
                record.employer_nssa
            )

            totals["paye"] += cls._decimal(
                record.paye
            )

            totals["aids_levy"] += cls._decimal(
                record.aids_levy
            )

            totals["other_deductions"] += cls._decimal(
                record.other_deductions_total
            )

            totals["total_deductions"] += cls._decimal(
                record.total_deductions
            )

            totals["net_pay"] += cls._decimal(
                record.net_pay
            )

            totals["employer_cost"] += cls._decimal(
                record.employer_cost
            )

        totals["total_tax"] = (
            totals["paye"]
            + totals["aids_levy"]
        )

        totals["total_nssa"] = (
            totals["employee_nssa"]
            + totals["employer_nssa"]
        )

        return {
            "records": records,
            "totals": totals,
        }

    @classmethod
    def get_department_summary(
        cls,
        period_id,
        search_term="",
    ):
        """
        Return payroll totals grouped by department.

        The optional search filter matches department names.
        """

        payroll_data = cls.get_payroll_summary(
            period_id=period_id,
        )

        search_term = search_term.strip().lower()

        departments = {}

        for record in payroll_data["records"]:
            department = record.employee.department

            if search_term:
                if search_term not in department.name.lower():
                    continue

            if department.id not in departments:
                departments[department.id] = {
                    "department_id": department.id,
                    "department_name": department.name,
                    "employee_count": 0,
                    "basic_salary": ZERO,
                    "overtime_amount": ZERO,
                    "allowances_total": ZERO,
                    "gross_pay": ZERO,
                    "employee_nssa": ZERO,
                    "employer_nssa": ZERO,
                    "paye": ZERO,
                    "aids_levy": ZERO,
                    "total_deductions": ZERO,
                    "net_pay": ZERO,
                    "employer_cost": ZERO,
                    "average_basic_salary": ZERO,
                    "average_gross_pay": ZERO,
                    "average_net_pay": ZERO,
                }

            department_row = departments[department.id]

            department_row["employee_count"] += 1

            department_row["basic_salary"] += cls._decimal(
                record.basic_salary
            )

            department_row["overtime_amount"] += cls._decimal(
                record.overtime_amount
            )

            department_row["allowances_total"] += cls._decimal(
                record.allowances_total
            )

            department_row["gross_pay"] += cls._decimal(
                record.gross_pay
            )

            department_row["employee_nssa"] += cls._decimal(
                record.nssa
            )

            department_row["employer_nssa"] += cls._decimal(
                record.employer_nssa
            )

            department_row["paye"] += cls._decimal(
                record.paye
            )

            department_row["aids_levy"] += cls._decimal(
                record.aids_levy
            )

            department_row["total_deductions"] += cls._decimal(
                record.total_deductions
            )

            department_row["net_pay"] += cls._decimal(
                record.net_pay
            )

            department_row["employer_cost"] += cls._decimal(
                record.employer_cost
            )

        department_rows = list(departments.values())

        for department_row in department_rows:
            employee_count = department_row[
                "employee_count"
            ]

            if employee_count:
                employee_count_decimal = Decimal(
                    employee_count
                )

                department_row[
                    "average_basic_salary"
                ] = (
                    department_row["basic_salary"]
                    / employee_count_decimal
                )

                department_row[
                    "average_gross_pay"
                ] = (
                    department_row["gross_pay"]
                    / employee_count_decimal
                )

                department_row[
                    "average_net_pay"
                ] = (
                    department_row["net_pay"]
                    / employee_count_decimal
                )

        department_rows.sort(
            key=lambda row: row[
                "department_name"
            ].lower()
        )

        totals = {
            "department_count": len(
                department_rows
            ),
            "employee_count": 0,
            "basic_salary": ZERO,
            "overtime_amount": ZERO,
            "allowances_total": ZERO,
            "gross_pay": ZERO,
            "employee_nssa": ZERO,
            "employer_nssa": ZERO,
            "paye": ZERO,
            "aids_levy": ZERO,
            "total_deductions": ZERO,
            "net_pay": ZERO,
            "employer_cost": ZERO,
            "average_basic_salary": ZERO,
            "average_gross_pay": ZERO,
            "average_net_pay": ZERO,
        }

        for department_row in department_rows:
            totals["employee_count"] += department_row[
                "employee_count"
            ]

            totals["basic_salary"] += department_row[
                "basic_salary"
            ]

            totals["overtime_amount"] += department_row[
                "overtime_amount"
            ]

            totals["allowances_total"] += department_row[
                "allowances_total"
            ]

            totals["gross_pay"] += department_row[
                "gross_pay"
            ]

            totals["employee_nssa"] += department_row[
                "employee_nssa"
            ]

            totals["employer_nssa"] += department_row[
                "employer_nssa"
            ]

            totals["paye"] += department_row[
                "paye"
            ]

            totals["aids_levy"] += department_row[
                "aids_levy"
            ]

            totals["total_deductions"] += department_row[
                "total_deductions"
            ]

            totals["net_pay"] += department_row[
                "net_pay"
            ]

            totals["employer_cost"] += department_row[
                "employer_cost"
            ]

        if totals["employee_count"]:
            employee_count_decimal = Decimal(
                totals["employee_count"]
            )

            totals["average_basic_salary"] = (
                totals["basic_salary"]
                / employee_count_decimal
            )

            totals["average_gross_pay"] = (
                totals["gross_pay"]
                / employee_count_decimal
            )

            totals["average_net_pay"] = (
                totals["net_pay"]
                / employee_count_decimal
            )

        return {
            "departments": department_rows,
            "totals": totals,
        }
