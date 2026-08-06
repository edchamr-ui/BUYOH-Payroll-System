"""Validation and transactional closing for payroll years."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    PayrollPeriod,
    PayrollRecord,
    PayrollYear,
    Payslip,
)
from app.services.audit_log_service import AuditLogService


class PayrollYearEndError(Exception):
    """Raised when a payroll year cannot be closed safely."""


@dataclass(frozen=True)
class YearEndCheck:
    """Represent one validation result."""

    code: str
    label: str
    passed: bool
    detail: str
    blocking: bool = True


@dataclass
class PayrollYearEndValidation:
    """Return the complete validation state for one payroll year."""

    payroll_year: PayrollYear
    checks: list[YearEndCheck] = field(default_factory=list)
    period_count: int = 0
    locked_period_count: int = 0
    payroll_record_count: int = 0
    payslip_count: int = 0
    missing_payslip_count: int = 0

    @property
    def blockers(self):
        return [
            check
            for check in self.checks
            if check.blocking and not check.passed
        ]

    @property
    def warnings(self):
        return [
            check
            for check in self.checks
            if not check.blocking and not check.passed
        ]

    @property
    def can_close(self):
        return (
            not self.payroll_year.is_closed
            and len(self.blockers) == 0
        )


class PayrollYearEndService:
    """Validate and close payroll years."""

    EXPECTED_CONFIRMATION = "CLOSE PAYROLL YEAR"

    @classmethod
    def validate_year(cls, payroll_year):
        """Run all year-end checks without changing data."""

        periods = list(
            PayrollPeriod.query
            .filter_by(
                payroll_year_id=payroll_year.id
            )
            .order_by(
                PayrollPeriod.month.asc()
            )
            .all()
        )

        period_ids = [
            period.id
            for period in periods
        ]

        if period_ids:
            payroll_record_count = (
                PayrollRecord.query
                .filter(
                    PayrollRecord.payroll_period_id.in_(
                        period_ids
                    )
                )
                .count()
            )

            payslip_count = (
                Payslip.query
                .join(
                    PayrollRecord,
                    Payslip.payroll_record_id
                    == PayrollRecord.id,
                )
                .filter(
                    PayrollRecord.payroll_period_id.in_(
                        period_ids
                    )
                )
                .count()
            )
        else:
            payroll_record_count = 0
            payslip_count = 0

        locked_periods = [
            period
            for period in periods
            if period.is_locked
        ]

        unlocked_periods = [
            period.period_name
            for period in periods
            if not period.is_locked
        ]

        period_months = {
            period.month
            for period in periods
        }

        missing_months = [
            month
            for month in range(1, 13)
            if month not in period_months
        ]

        missing_payslip_count = max(
            payroll_record_count - payslip_count,
            0,
        )

        checks = [
            YearEndCheck(
                code="year_status",
                label="Payroll year is open",
                passed=payroll_year.is_open,
                detail=(
                    f"Current status: {payroll_year.status}."
                ),
            ),
            YearEndCheck(
                code="twelve_periods",
                label="All 12 payroll periods exist",
                passed=len(periods) == 12,
                detail=(
                    "All monthly periods are present."
                    if len(periods) == 12
                    else (
                        f"{len(periods)}/12 periods exist. "
                        f"Missing month numbers: {missing_months}."
                    )
                ),
            ),
            YearEndCheck(
                code="all_locked",
                label="All payroll periods are locked",
                passed=(
                    len(periods) == 12
                    and len(locked_periods) == 12
                ),
                detail=(
                    "Every monthly payroll period is locked."
                    if len(periods) == 12
                    and len(locked_periods) == 12
                    else (
                        f"{len(locked_periods)}/12 periods are locked. "
                        f"Not locked: {', '.join(unlocked_periods) or 'None'}."
                    )
                ),
            ),
            YearEndCheck(
                code="payroll_records",
                label="Payroll records exist",
                passed=payroll_record_count > 0,
                detail=(
                    f"{payroll_record_count} payroll record(s) found."
                ),
            ),
            YearEndCheck(
                code="payslips_complete",
                label="Every payroll record has a payslip",
                passed=(
                    payroll_record_count > 0
                    and missing_payslip_count == 0
                ),
                detail=(
                    f"{payslip_count} payslip(s) found; "
                    f"{missing_payslip_count} missing."
                ),
            ),
        ]

        return PayrollYearEndValidation(
            payroll_year=payroll_year,
            checks=checks,
            period_count=len(periods),
            locked_period_count=len(locked_periods),
            payroll_record_count=payroll_record_count,
            payslip_count=payslip_count,
            missing_payslip_count=missing_payslip_count,
        )

    @classmethod
    def close_year(
        cls,
        *,
        payroll_year,
        closed_by_user_id,
        closing_reason,
    ):
        """Close a payroll year in one database transaction."""

        validation = cls.validate_year(
            payroll_year
        )

        if payroll_year.is_closed:
            raise PayrollYearEndError(
                f"Payroll year {payroll_year.year} is already closed."
            )

        if not validation.can_close:
            blocker_labels = ", ".join(
                check.label
                for check in validation.blockers
            )

            raise PayrollYearEndError(
                (
                    "The payroll year cannot be closed until "
                    f"these checks pass: {blocker_labels}."
                )
            )

        now = datetime.utcnow()

        try:
            payroll_year.status = PayrollYear.STATUS_CLOSED
            payroll_year.closing_started_at = (
                payroll_year.closing_started_at
                or now
            )
            payroll_year.closing_started_by_user_id = (
                payroll_year.closing_started_by_user_id
                or closed_by_user_id
            )
            payroll_year.closed_at = now
            payroll_year.closed_by_user_id = closed_by_user_id
            payroll_year.closing_reason = closing_reason.strip()

            AuditLogService.log(
                user_id=closed_by_user_id,
                action="Payroll Year Closed",
                entity_type="PayrollYear",
                entity_id=payroll_year.id,
                description=(
                    f"Closed payroll year {payroll_year.year}. "
                    f"Periods: {validation.period_count}; "
                    f"payroll records: {validation.payroll_record_count}; "
                    f"payslips: {validation.payslip_count}. "
                    f"Reason: {closing_reason.strip()}"
                ),
                commit=False,
            )

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()

            raise PayrollYearEndError(
                "The payroll year could not be closed. "
                "No year-end changes were committed."
            ) from error

        return validation
