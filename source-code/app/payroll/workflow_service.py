"""Payroll approval and locking workflow service."""

from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.payroll_period import PayrollPeriod
from app.services.audit_log_service import AuditLogService
from app.time_utils import legacy_utc_now


class PayrollWorkflowError(Exception):
    """Raised when an invalid payroll workflow action is attempted."""


class PayrollWorkflowService:
    """Manage payroll approval, locking and reopening."""

    @staticmethod
    def approve_period(
        payroll_period: PayrollPeriod,
        user_id: int,
    ) -> PayrollPeriod:
        """
        Approve a processed payroll period.

        Valid transition:
            Processed -> Approved
        """

        if payroll_period.status != "Processed":
            raise PayrollWorkflowError(
                "Only a processed payroll period can be approved."
            )

        if not payroll_period.payroll_records:
            raise PayrollWorkflowError(
                "Cannot approve payroll because no payroll "
                "records exist."
            )

        try:
            payroll_period.status = "Approved"
            payroll_period.approved_by = user_id
            payroll_period.approved_at = legacy_utc_now()

            AuditLogService.log(
                user_id=user_id,
                action="Payroll Approved",
                entity_type="PayrollPeriod",
                entity_id=payroll_period.id,
                description=(
                    f"Approved payroll for "
                    f"{payroll_period.period_name}."
                ),
                commit=False,
            )

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()

            raise PayrollWorkflowError(
                "Payroll approval could not be saved."
            ) from error

        return payroll_period

    @staticmethod
    def lock_period(
        payroll_period: PayrollPeriod,
        user_id: int,
    ) -> PayrollPeriod:
        """
        Lock an approved payroll period.

        Valid transition:
            Approved -> Locked
        """

        if payroll_period.status != "Approved":
            raise PayrollWorkflowError(
                "Only an approved payroll period can be locked."
            )

        if not payroll_period.payroll_records:
            raise PayrollWorkflowError(
                "Cannot lock payroll because the payroll "
                "register is empty."
            )

        try:
            payroll_period.status = "Locked"
            payroll_period.locked_by = user_id
            payroll_period.locked_at = legacy_utc_now()

            AuditLogService.log(
                user_id=user_id,
                action="Payroll Locked",
                entity_type="PayrollPeriod",
                entity_id=payroll_period.id,
                description=(
                    f"Locked payroll for "
                    f"{payroll_period.period_name}."
                ),
                commit=False,
            )

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()

            raise PayrollWorkflowError(
                "Payroll locking could not be saved."
            ) from error

        return payroll_period

    @staticmethod
    def reopen_period(
        payroll_period: PayrollPeriod,
        user_id: int,
    ) -> PayrollPeriod:
        """
        Reopen a locked payroll period.

        Valid transition:
            Locked -> Processed
        """

        if payroll_period.status != "Locked":
            raise PayrollWorkflowError(
                "Only a locked payroll period can be reopened."
            )

        try:
            payroll_period.status = "Processed"

            payroll_period.approved_by = None
            payroll_period.approved_at = None
            payroll_period.locked_by = None
            payroll_period.locked_at = None

            AuditLogService.log(
                user_id=user_id,
                action="Payroll Reopened",
                entity_type="PayrollPeriod",
                entity_id=payroll_period.id,
                description=(
                    f"Reopened payroll for "
                    f"{payroll_period.period_name}."
                ),
                commit=False,
            )

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()

            raise PayrollWorkflowError(
                "Payroll reopening could not be saved."
            ) from error

        return payroll_period

    @staticmethod
    def ensure_editable(
        payroll_period: PayrollPeriod,
    ) -> None:
        """Prevent changes to approved or locked payroll."""

        if payroll_period.status == "Approved":
            raise PayrollWorkflowError(
                "Approved payroll cannot be modified."
            )

        if payroll_period.status == "Locked":
            raise PayrollWorkflowError(
                "Locked payroll cannot be modified."
            )

    @staticmethod
    def ensure_processable(
        payroll_period: PayrollPeriod,
    ) -> None:
        """Validate that the payroll period may be processed."""

        if payroll_period.status != "Draft":
            raise PayrollWorkflowError(
                "Only draft payroll periods can be processed."
            )
