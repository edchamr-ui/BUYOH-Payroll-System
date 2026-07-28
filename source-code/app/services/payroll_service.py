"""Payroll processing and register service."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Employee, PayrollRecord
from app.services.audit_log_service import AuditLogService
from app.services.payroll_calculator import (
    PayrollCalculator,
    ZERO,
)
from app.services.statutory_rule_service import (
    StatutoryRuleService,
    StatutoryRuleServiceError,
)


class PayrollServiceError(Exception):
    """Base exception for payroll service failures."""


class InvalidPayrollStatusError(PayrollServiceError):
    """Raised when a payroll period cannot be processed."""


class NoActiveEmployeesError(PayrollServiceError):
    """Raised when there are no active employees to process."""


class PayrollConfigurationError(PayrollServiceError):
    """Raised when statutory payroll configuration is unavailable."""


class PayrollPersistenceError(PayrollServiceError):
    """Raised when payroll records cannot be saved."""


@dataclass(frozen=True)
class PayrollProcessingResult:
    """Summary returned after processing a payroll period."""

    created_count: int
    skipped_count: int
    rule_set_name: str
    currency: str
    calculation_date: date


@dataclass(frozen=True)
class PayrollRegisterSummary:
    """Calculated totals for a payroll register."""

    employee_count: int
    total_basic_salary: Decimal
    total_gross_pay: Decimal
    total_deductions: Decimal
    total_net_pay: Decimal
    total_employer_nssa: Decimal
    total_employer_cost: Decimal


class PayrollService:
    """Coordinate payroll processing and register reporting."""

    DEFAULT_CURRENCY = "USD"

    @staticmethod
    def get_period_records(period):
        """Return payroll records for one payroll period."""

        return (
            PayrollRecord.query
            .filter_by(
                payroll_period_id=period.id
            )
            .order_by(
                PayrollRecord.id.asc()
            )
            .all()
        )

    @staticmethod
    def _decimal_value(value):
        """Safely convert a database value into Decimal."""

        if value is None:
            return ZERO

        return Decimal(str(value))

    @classmethod
    def calculate_register_summary(
        cls,
        records,
    ):
        """Calculate totals for a payroll register."""

        return PayrollRegisterSummary(
            employee_count=len(records),

            total_basic_salary=sum(
                (
                    cls._decimal_value(
                        record.basic_salary
                    )
                    for record in records
                ),
                ZERO,
            ),

            total_gross_pay=sum(
                (
                    cls._decimal_value(
                        record.gross_pay
                    )
                    for record in records
                ),
                ZERO,
            ),

            total_deductions=sum(
                (
                    cls._decimal_value(
                        record.total_deductions
                    )
                    for record in records
                ),
                ZERO,
            ),

            total_net_pay=sum(
                (
                    cls._decimal_value(
                        record.net_pay
                    )
                    for record in records
                ),
                ZERO,
            ),

            total_employer_nssa=sum(
                (
                    cls._decimal_value(
                        record.employer_nssa
                    )
                    for record in records
                ),
                ZERO,
            ),

            total_employer_cost=sum(
                (
                    cls._decimal_value(
                        record.employer_cost
                    )
                    for record in records
                ),
                ZERO,
            ),
        )

    @staticmethod
    def _get_calculation_date(period):
        """
        Determine the statutory calculation date.

        Payment date is preferred because statutory rules
        normally apply according to the payroll payment date.
        The period end date is used as a fallback.
        """

        calculation_date = (
            period.payment_date
            or period.end_date
        )

        if calculation_date is None:
            raise PayrollConfigurationError(
                "The payroll period must have a payment "
                "date or an end date before it can be "
                "processed."
            )

        if isinstance(
            calculation_date,
            datetime,
        ):
            calculation_date = (
                calculation_date.date()
            )

        if not isinstance(
            calculation_date,
            date,
        ):
            raise PayrollConfigurationError(
                "The payroll calculation date is invalid."
            )

        return calculation_date

    @classmethod
    def _load_statutory_configuration(
        cls,
        period,
        currency,
    ):
        """Load calculator configuration from PostgreSQL."""

        calculation_date = (
            cls._get_calculation_date(period)
        )

        try:
            rule_set = (
                StatutoryRuleService
                .get_applicable_rule_set(
                    calculation_date=calculation_date,
                    currency=currency,
                )
            )

            statutory_config = (
                StatutoryRuleService
                .to_configuration(rule_set)
            )

        except StatutoryRuleServiceError as error:
            raise PayrollConfigurationError(
                "Payroll could not find an applicable "
                "statutory rule set. "
                f"Currency: {currency}; "
                f"calculation date: "
                f"{calculation_date.isoformat()}. "
                f"{error}"
            ) from error

        return (
            rule_set,
            statutory_config,
            calculation_date,
        )

    @classmethod
    def process_period(
        cls,
        period,
        processed_by_user_id,
        currency=DEFAULT_CURRENCY,
    ):
        """
        Create payroll records for active employees.

        Valid transition:
            Draft -> Processed

        The payroll records, period status and audit entry
        are committed in the same database transaction.
        """

        if period.status != "Draft":
            raise InvalidPayrollStatusError(
                "Only draft payroll periods can be processed."
            )

        normalized_currency = (
            str(currency)
            .strip()
            .upper()
        )

        if not normalized_currency:
            raise PayrollConfigurationError(
                "Payroll currency is required."
            )

        (
            rule_set,
            statutory_config,
            calculation_date,
        ) = cls._load_statutory_configuration(
            period=period,
            currency=normalized_currency,
        )

        active_employees = (
            Employee.query
            .filter_by(is_active=True)
            .order_by(
                Employee.employee_number.asc()
            )
            .all()
        )

        if not active_employees:
            raise NoActiveEmployeesError(
                "No active employees were found."
            )

        existing_employee_ids = {
            employee_id
            for employee_id, in (
                db.session.query(
                    PayrollRecord.employee_id
                )
                .filter(
                    PayrollRecord.payroll_period_id
                    == period.id
                )
                .all()
            )
        }

        created_count = 0
        skipped_count = 0

        try:
            for employee in active_employees:

                if employee.id in existing_employee_ids:
                    skipped_count += 1
                    continue

                calculation = PayrollCalculator(
                    basic_salary=employee.basic_salary,
                    statutory_config=statutory_config,
                ).calculate()

                payroll_record = PayrollRecord(
                    payroll_period_id=period.id,
                    employee_id=employee.id,
                    processed_by=processed_by_user_id,

                    basic_salary=(
                        calculation.basic_salary
                    ),

                    overtime_amount=(
                        calculation.overtime_amount
                    ),

                    allowances_total=(
                        calculation.allowances_total
                    ),

                    gross_pay=(
                        calculation.gross_pay
                    ),

                    nssa=calculation.nssa,

                    employer_nssa=(
                        calculation.employer_nssa
                    ),

                    paye=calculation.paye,

                    aids_levy=(
                        calculation.aids_levy
                    ),

                    other_deductions_total=(
                        calculation
                        .other_deductions_total
                    ),

                    total_deductions=(
                        calculation.total_deductions
                    ),

                    net_pay=(
                        calculation.net_pay
                    ),

                    employer_cost=(
                        calculation.employer_cost
                    ),

                    status="Draft",
                )

                db.session.add(payroll_record)

                created_count += 1

            if created_count == 0:
                raise PayrollPersistenceError(
                    "No new payroll records were created."
                )

            period.status = "Processed"

            AuditLogService.log(
                user_id=processed_by_user_id,
                action="Payroll Processed",
                entity_type="PayrollPeriod",
                entity_id=period.id,
                description=(
                    f"Processed payroll for "
                    f"{period.period_name}. "
                    f"Created {created_count} payroll "
                    f"record(s) using the "
                    f"{rule_set.display_name} rule set."
                ),
                commit=False,
            )

            db.session.commit()

        except PayrollPersistenceError:
            db.session.rollback()
            raise

        except (
            SQLAlchemyError,
            ValueError,
        ) as error:
            db.session.rollback()

            raise PayrollPersistenceError(
                "Payroll processing failed. No new payroll "
                "records or audit entries were saved."
            ) from error

        return PayrollProcessingResult(
            created_count=created_count,
            skipped_count=skipped_count,
            rule_set_name=rule_set.display_name,
            currency=normalized_currency,
            calculation_date=calculation_date,
        )
