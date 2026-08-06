"""Administrator-only payroll reset service."""

from dataclasses import dataclass, field
from pathlib import Path
import shutil

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    Allowance,
    AuditLog,
    Deduction,
    EmailDelivery,
    EmployeeAllowance,
    EmployeeDeduction,
    PayrollPeriod,
    PayrollRecord,
    PayrollYear,
    Payslip,
)
from app.services.audit_log_service import AuditLogService


class PayrollResetError(Exception):
    """Raised when a payroll reset operation cannot be completed."""


@dataclass(frozen=True)
class PayrollResetPreview:
    """Current record counts displayed in the reset centre."""

    payroll_years: int
    payroll_periods: int
    payroll_records: int
    historical_allowances: int
    historical_deductions: int
    payslips: int
    email_deliveries: int
    recurring_allowances: int
    recurring_deductions: int
    audit_logs: int


@dataclass
class PayrollResetResult:
    """Summary of one completed reset operation."""

    deleted_counts: dict[str, int] = field(
        default_factory=dict
    )

    removed_files: int = 0

    file_warnings: list[str] = field(
        default_factory=list
    )


class PayrollResetService:
    """Perform protected payroll-domain reset operations."""

    GENERATED_PAYSLIP_DIRECTORY = (
        Path("instance")
        / "generated_payslips"
    )

    @classmethod
    def preview(cls):
        """Return current reset-impact counts."""

        return PayrollResetPreview(
            payroll_years=PayrollYear.query.count(),
            payroll_periods=PayrollPeriod.query.count(),
            payroll_records=PayrollRecord.query.count(),
            historical_allowances=Allowance.query.count(),
            historical_deductions=Deduction.query.count(),
            payslips=Payslip.query.count(),
            email_deliveries=EmailDelivery.query.count(),
            recurring_allowances=(
                EmployeeAllowance.query.count()
            ),
            recurring_deductions=(
                EmployeeDeduction.query.count()
            ),
            audit_logs=AuditLog.query.count(),
        )

    @staticmethod
    def _capture_payslip_files():
        """Capture generated payslip paths before deletion."""

        paths = []

        for payslip in Payslip.query.all():
            raw_path = str(
                getattr(
                    payslip,
                    "file_path",
                    "",
                )
                or ""
            ).strip()

            if raw_path:
                paths.append(
                    Path(raw_path)
                )

        return paths

    @staticmethod
    def _bulk_delete(model):
        """Delete all rows for a model and return the count."""

        return (
            db.session
            .query(model)
            .delete(
                synchronize_session=False
            )
        )

    @classmethod
    def _remove_generated_files(
        cls,
        tracked_paths,
    ):
        """Remove generated PDFs after database reset."""

        removed_files = 0
        warnings = []

        for file_path in tracked_paths:
            try:
                if file_path.is_file():
                    file_path.unlink()
                    removed_files += 1

            except OSError as error:
                warnings.append(
                    f"{file_path}: {error}"
                )

        try:
            if (
                cls.GENERATED_PAYSLIP_DIRECTORY
                .exists()
            ):
                remaining_files = [
                    path
                    for path in (
                        cls.GENERATED_PAYSLIP_DIRECTORY
                        .rglob("*")
                    )
                    if path.is_file()
                ]

                removed_files += len(
                    remaining_files
                )

                shutil.rmtree(
                    cls.GENERATED_PAYSLIP_DIRECTORY
                )

        except OSError as error:
            warnings.append(
                (
                    f"{cls.GENERATED_PAYSLIP_DIRECTORY}: "
                    f"{error}"
                )
            )

        return removed_files, warnings

    @classmethod
    def clear_payroll_history(
        cls,
        *,
        administrator_id,
    ):
        """
        Delete payroll history while preserving years,
        periods, recurring configuration and master data.
        """

        tracked_paths = (
            cls._capture_payslip_files()
        )

        deleted_counts = {}

        try:
            deleted_counts[
                "email_deliveries"
            ] = cls._bulk_delete(
                EmailDelivery
            )

            deleted_counts[
                "payslips"
            ] = cls._bulk_delete(
                Payslip
            )

            deleted_counts[
                "historical_allowances"
            ] = cls._bulk_delete(
                Allowance
            )

            deleted_counts[
                "historical_deductions"
            ] = cls._bulk_delete(
                Deduction
            )

            deleted_counts[
                "payroll_records"
            ] = cls._bulk_delete(
                PayrollRecord
            )

            deleted_counts[
                "audit_logs"
            ] = cls._bulk_delete(
                AuditLog
            )

            db.session.commit()

            AuditLogService.log(
                user_id=administrator_id,
                action=(
                    "Payroll History Reset"
                ),
                entity_type="PayrollReset",
                description=(
                    "Deleted payroll records, historical "
                    "earnings and deductions, payslips, "
                    "email history and prior audit logs. "
                    "Payroll years, payroll periods, "
                    "recurring configuration and master "
                    "data were preserved."
                ),
                commit=True,
            )

        except SQLAlchemyError as error:
            db.session.rollback()

            raise PayrollResetError(
                (
                    "Payroll history could not "
                    "be deleted."
                )
            ) from error

        removed_files, warnings = (
            cls._remove_generated_files(
                tracked_paths
            )
        )

        return PayrollResetResult(
            deleted_counts=deleted_counts,
            removed_files=removed_files,
            file_warnings=warnings,
        )

    @classmethod
    def clear_payroll_configuration(
        cls,
        *,
        administrator_id,
    ):
        """
        Delete recurring employee allowances and
        recurring employee deductions only.
        """

        deleted_counts = {}

        try:
            deleted_counts[
                "recurring_allowances"
            ] = cls._bulk_delete(
                EmployeeAllowance
            )

            deleted_counts[
                "recurring_deductions"
            ] = cls._bulk_delete(
                EmployeeDeduction
            )

            AuditLogService.log(
                user_id=administrator_id,
                action=(
                    "Payroll Configuration Reset"
                ),
                entity_type="PayrollReset",
                description=(
                    "Deleted recurring employee allowance "
                    "and deduction assignments. Employees, "
                    "payroll years, payroll periods and "
                    "payroll history were preserved."
                ),
                commit=False,
            )

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()

            raise PayrollResetError(
                (
                    "Payroll configuration could "
                    "not be deleted."
                )
            ) from error

        return PayrollResetResult(
            deleted_counts=deleted_counts,
        )

    @classmethod
    def factory_reset_payroll(
        cls,
        *,
        administrator_id,
    ):
        """
        Delete the payroll domain while preserving
        employees, departments, users, company settings
        and statutory configuration.
        """

        tracked_paths = (
            cls._capture_payslip_files()
        )

        deleted_counts = {}

        try:
            # Delete child records first.
            deleted_counts[
                "email_deliveries"
            ] = cls._bulk_delete(
                EmailDelivery
            )

            deleted_counts[
                "payslips"
            ] = cls._bulk_delete(
                Payslip
            )

            deleted_counts[
                "historical_allowances"
            ] = cls._bulk_delete(
                Allowance
            )

            deleted_counts[
                "historical_deductions"
            ] = cls._bulk_delete(
                Deduction
            )

            deleted_counts[
                "payroll_records"
            ] = cls._bulk_delete(
                PayrollRecord
            )

            deleted_counts[
                "recurring_allowances"
            ] = cls._bulk_delete(
                EmployeeAllowance
            )

            deleted_counts[
                "recurring_deductions"
            ] = cls._bulk_delete(
                EmployeeDeduction
            )

            # Delete monthly periods before their parent years.
            deleted_counts[
                "payroll_periods"
            ] = cls._bulk_delete(
                PayrollPeriod
            )

            deleted_counts[
                "payroll_years"
            ] = cls._bulk_delete(
                PayrollYear
            )

            deleted_counts[
                "audit_logs"
            ] = cls._bulk_delete(
                AuditLog
            )

            db.session.commit()

            AuditLogService.log(
                user_id=administrator_id,
                action=(
                    "Payroll Factory Reset"
                ),
                entity_type="PayrollReset",
                description=(
                    "Deleted payroll years, payroll periods, "
                    "payroll records, payslips, email history, "
                    "historical earnings and deductions, "
                    "recurring payroll assignments and prior "
                    "audit logs. Employees, departments, "
                    "users, company settings and statutory "
                    "configuration were preserved."
                ),
                commit=True,
            )

        except SQLAlchemyError as error:
            db.session.rollback()

            raise PayrollResetError(
                (
                    "The payroll factory reset "
                    "could not be completed."
                )
            ) from error

        removed_files, warnings = (
            cls._remove_generated_files(
                tracked_paths
            )
        )

        return PayrollResetResult(
            deleted_counts=deleted_counts,
            removed_files=removed_files,
            file_warnings=warnings,
        )
