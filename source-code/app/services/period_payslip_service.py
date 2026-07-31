"""Generate missing individual payslips for a payroll period."""

from dataclasses import dataclass, field

from app.services.payslip_service import (
    PayslipGenerationError,
    PayslipRecordNotFoundError,
    PayslipService,
)


class PeriodPayslipServiceError(Exception):
    """Base exception for period payslip generation failures."""


class InvalidPeriodPayslipStatusError(
    PeriodPayslipServiceError
):
    """Raised when payslips cannot be generated for a period."""


class EmptyPayrollRegisterError(
    PeriodPayslipServiceError
):
    """Raised when the payroll period has no payroll records."""


@dataclass(frozen=True)
class PayslipGenerationFailure:
    """Describe one failed employee payslip generation."""

    payroll_record_id: int
    employee_name: str
    message: str


@dataclass
class PeriodPayslipResult:
    """Summary of a period-level payslip generation operation."""

    generated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0

    failures: list[PayslipGenerationFailure] = field(
        default_factory=list
    )


class PeriodPayslipService:
    """Generate missing individual payslips for one period."""

    ALLOWED_STATUSES = {
        "Processed",
        "Approved",
        "Paid",
        "Locked",
    }

    @staticmethod
    def _employee_name(payroll_record):
        """Return a payroll record employee's full name."""

        employee = payroll_record.employee

        full_name = getattr(
            employee,
            "full_name",
            None,
        )

        if full_name:
            return str(full_name).strip()

        first_name = str(
            getattr(
                employee,
                "first_name",
                "",
            )
            or ""
        ).strip()

        last_name = str(
            getattr(
                employee,
                "last_name",
                "",
            )
            or ""
        ).strip()

        return (
            f"{first_name} {last_name}".strip()
            or f"Employee {employee.id}"
        )

    @classmethod
    def generate_missing(
        cls,
        *,
        payroll_period,
        generated_by_user_id,
    ):
        """
        Generate individual PDFs only where no Payslip record exists.

        Existing payslips are skipped and are not overwritten.
        """

        if payroll_period.status not in cls.ALLOWED_STATUSES:
            raise InvalidPeriodPayslipStatusError(
                "Individual payslips can only be generated for "
                "processed, approved, paid or locked payroll periods."
            )

        payroll_records = list(
            payroll_period.payroll_records
        )

        if not payroll_records:
            raise EmptyPayrollRegisterError(
                "This payroll period has no payroll records."
            )

        result = PeriodPayslipResult()

        for payroll_record in payroll_records:
            if payroll_record.payslip is not None:
                result.skipped_count += 1
                continue

            employee_name = cls._employee_name(
                payroll_record
            )

            try:
                PayslipService.generate_payslip(
                    payroll_record_id=payroll_record.id,
                    generated_by_user_id=generated_by_user_id,
                )

            except (
                PayslipRecordNotFoundError,
                PayslipGenerationError,
            ) as error:
                result.failed_count += 1

                result.failures.append(
                    PayslipGenerationFailure(
                        payroll_record_id=payroll_record.id,
                        employee_name=employee_name,
                        message=str(error),
                    )
                )

            else:
                result.generated_count += 1

        return result
