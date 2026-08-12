"""Payroll processing and register service."""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    Allowance,
    Deduction,
    Employee,
    PayrollPeriod,
    PayrollRecord,
)
from app.models.payroll_ssp_input import PayrollSSPInput
from app.models.payroll_smp_input import PayrollSMPInput
from app.models.payroll_spp_input import PayrollSPPInput
from app.models.payroll_sap_input import PayrollSAPInput
from app.models.payroll_shpp_input import PayrollShPPInput
from app.models.payroll_spbp_input import PayrollSPBPInput
from app.services.audit_log_service import AuditLogService
from app.services.payroll_calculator import ZERO
from app.services.statutory_engines import (
    StatutoryEngineRegistry,
    StatutoryEngineRegistryError,
)
from app.services.statutory_engines.base import (
    StatutoryEngineError,
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
    provisional_rule_used: bool
    rule_effective_to: date | None


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

    @classmethod
    def _assignment_amount(cls, assignment, definition, basic_salary):
        """Calculate one recurring assignment using employee overrides."""

        if definition.calculation_method == "Percentage":
            percentage = cls._decimal_value(assignment.percentage)
            if percentage == ZERO:
                percentage = cls._decimal_value(
                    definition.default_percentage
                )
            return (cls._decimal_value(basic_salary) * percentage / 100).quantize(
                Decimal("0.01")
            )

        amount = cls._decimal_value(assignment.amount)
        if amount == ZERO:
            amount = cls._decimal_value(definition.default_amount)
        return amount.quantize(Decimal("0.01"))

    @staticmethod
    def _is_assignment_active(assignment, definition, calculation_date):
        return bool(
            assignment.is_active
            and definition is not None
            and definition.is_active
            and (
                assignment.start_date is None
                or assignment.start_date <= calculation_date
            )
            and (
                assignment.end_date is None
                or assignment.end_date >= calculation_date
            )
        )

    @classmethod
    def _recurring_pay_components(cls, employee, calculation_date):
        """Return payroll totals and historical line-item snapshots."""

        allowance_lines = []
        deduction_lines = []
        cash_allowances = ZERO
        taxable_cash_allowances = ZERO
        non_cash_benefits = ZERO
        net_pay_deductions = ZERO
        allowable_deductions = ZERO
        regular_variable_pay = ZERO
        occasional_irregular_pay = ZERO

        for assignment in employee.recurring_allowances:
            definition = assignment.allowance_type
            if not cls._is_assignment_active(
                assignment, definition, calculation_date
            ):
                continue

            amount = cls._assignment_amount(
                assignment, definition, employee.basic_salary
            )
            if amount == ZERO:
                continue

            classification = definition.earning_classification
            is_benefit = (
                classification == definition.EARNING_TAXABLE_BENEFIT
            )
            if is_benefit:
                if definition.is_taxable:
                    non_cash_benefits += amount
            else:
                cash_allowances += amount
                if definition.is_taxable:
                    taxable_cash_allowances += amount
                    if classification == definition.EARNING_COMMISSION:
                        regular_variable_pay += amount
                    elif classification == definition.EARNING_BONUS:
                        occasional_irregular_pay += amount

            allowance_lines.append((assignment, definition, amount))

        for assignment in employee.recurring_deductions:
            definition = assignment.deduction_type
            if not cls._is_assignment_active(
                assignment, definition, calculation_date
            ):
                continue

            amount = cls._assignment_amount(
                assignment, definition, employee.basic_salary
            )
            if amount == ZERO:
                continue

            if definition.reduces_net_pay:
                net_pay_deductions += amount
            if definition.is_tax_deductible:
                allowable_deductions += amount
            deduction_lines.append((assignment, definition, amount))

        return {
            "cash_allowances": cash_allowances,
            "taxable_cash_allowances": taxable_cash_allowances,
            "non_cash_benefits": non_cash_benefits,
            "net_pay_deductions": net_pay_deductions,
            "allowable_deductions": allowable_deductions,
            "regular_variable_pay": regular_variable_pay,
            "occasional_irregular_pay": occasional_irregular_pay,
            "allowance_lines": allowance_lines,
            "deduction_lines": deduction_lines,
        }

    @classmethod
    def _botswana_ytd_context(cls, employee_id, calculation_date):
        """Return prior July-June values required by BURS spread-back PAYE."""

        tax_year_start = date(
            calculation_date.year if calculation_date.month >= 7
            else calculation_date.year - 1,
            7,
            1,
        )
        records = (
            PayrollRecord.query
            .join(PayrollPeriod)
            .filter(
                PayrollRecord.employee_id == employee_id,
                PayrollPeriod.payment_date >= tax_year_start,
                PayrollPeriod.payment_date < calculation_date,
            )
            .order_by(PayrollPeriod.payment_date.asc())
            .all()
        )

        taxable_income = ZERO
        variable_income = ZERO
        regular_paye = ZERO
        for record in records:
            taxable_allowances = ZERO
            allowable_deductions = ZERO
            for line in record.allowances:
                if not line.is_taxable:
                    continue
                if line.earning_classification == "Bonus":
                    continue
                taxable_allowances += cls._decimal_value(line.amount)
                if line.earning_classification == "Commission":
                    variable_income += cls._decimal_value(line.amount)
            for line in record.deductions:
                if line.is_tax_deductible:
                    allowable_deductions += cls._decimal_value(line.amount)
            taxable_income += max(
                ZERO,
                cls._decimal_value(record.basic_salary)
                + cls._decimal_value(record.overtime_amount)
                + taxable_allowances
                - cls._decimal_value(record.nssa)
                - allowable_deductions,
            )
            regular_paye += cls._decimal_value(record.regular_paye)

        return {
            "elapsed_payments": len(records),
            "regular_taxable_income": taxable_income,
            "regular_variable_income": variable_income,
            "regular_paye": regular_paye,
        }

    @staticmethod
    def _uk_tax_month(calculation_date):
        """Return HMRC tax month 1-12 for a payment date."""

        shifted_date = calculation_date - timedelta(days=5)
        tax_year_start_year = (
            shifted_date.year
            if shifted_date.month >= 4
            else shifted_date.year - 1
        )
        return (
            (shifted_date.year - tax_year_start_year) * 12
            + shifted_date.month
            - 3
        )

    @staticmethod
    def _uk_history_records(employee_id, calculation_date):
        """Load earlier UK payroll snapshots in the current tax year."""

        tax_year_start = date(
            calculation_date.year
            if calculation_date >= date(calculation_date.year, 4, 6)
            else calculation_date.year - 1,
            4,
            6,
        )
        return (
            PayrollRecord.query
            .join(PayrollPeriod)
            .filter(
                PayrollRecord.employee_id == employee_id,
                PayrollPeriod.payment_date >= tax_year_start,
                PayrollPeriod.payment_date < calculation_date,
                PayrollRecord.uk_taxable_pay.isnot(None),
            )
            .order_by(PayrollPeriod.payment_date.asc())
            .all()
        )

    @classmethod
    def _uk_ytd_context(cls, employee_id, calculation_date):
        """Return prior PAYE and Class 1 NI values for the UK tax year."""

        records = cls._uk_history_records(
            employee_id,
            calculation_date,
        )
        return {
            "taxable_pay": sum(
                (cls._decimal_value(row.uk_taxable_pay) for row in records),
                ZERO,
            ),
            "tax_paid": sum(
                (cls._decimal_value(row.paye) for row in records),
                ZERO,
            ),
            "ni_earnings": sum(
                (cls._decimal_value(row.gross_pay) for row in records),
                ZERO,
            ),
            "employee_ni": sum(
                (cls._decimal_value(row.nssa) for row in records),
                ZERO,
            ),
            "employer_ni": sum(
                (cls._decimal_value(row.employer_nssa) for row in records),
                ZERO,
            ),
            "elapsed_payments": len(records),
        }

    @classmethod
    def _uk_prior_ssp_paid_days(cls, employee_id, calculation_date):
        """Return paid SSP qualifying days already used in the tax year."""

        return sum(
            int(getattr(row, "uk_ssp_payable_days", 0) or 0)
            for row in cls._uk_history_records(employee_id, calculation_date)
        )

    @staticmethod
    def _uk_smp_history_records(
        employee_id,
        maternity_pay_period_start,
        calculation_date,
    ):
        """Load prior snapshots for the same maternity pay period."""

        return (
            PayrollRecord.query
            .join(PayrollPeriod)
            .filter(
                PayrollRecord.employee_id == employee_id,
                PayrollRecord.uk_smp_mpp_start_date
                == maternity_pay_period_start,
                PayrollPeriod.payment_date < calculation_date,
            )
            .order_by(PayrollPeriod.payment_date.asc())
            .all()
        )

    @classmethod
    def _uk_prior_smp_paid_days(
        cls,
        employee_id,
        maternity_pay_period_start,
        calculation_date,
    ):
        """Return SMP days already paid for this maternity pay period."""

        return sum(
            int(getattr(row, "uk_smp_paid_days", 0) or 0)
            for row in cls._uk_smp_history_records(
                employee_id,
                maternity_pay_period_start,
                calculation_date,
            )
        )

    @classmethod
    def _uk_smp_snapshot(
        cls,
        *,
        employee,
        period,
        statutory_engine,
        statutory_config,
        calculation_date,
    ):
        """Calculate period SMP input and return pay/snapshot values."""

        entry = PayrollSMPInput.query.filter_by(
            payroll_period_id=period.id,
            employee_id=employee.id,
        ).one_or_none()
        if entry is None:
            return ZERO, ZERO, {}

        if not entry.eligibility_confirmed:
            raise PayrollConfigurationError(
                f"SMP eligibility is not confirmed for employee "
                f"{employee.employee_number}."
            )
        if not entry.matb1_received:
            raise PayrollConfigurationError(
                f"MATB1 evidence is not recorded for employee "
                f"{employee.employee_number}."
            )

        contractual_salary = cls._decimal_value(employee.basic_salary)
        salary_withheld = cls._decimal_value(entry.salary_withheld)
        if salary_withheld > contractual_salary:
            raise PayrollConfigurationError(
                "SMP salary withheld cannot exceed the employee's "
                "contractual basic salary."
            )

        prior_paid_days = cls._uk_prior_smp_paid_days(
            employee.id,
            entry.maternity_pay_period_start,
            calculation_date,
        )
        try:
            result = statutory_engine.calculate_statutory_maternity_pay(
                average_weekly_earnings=entry.average_weekly_earnings,
                paid_days=entry.paid_days,
                prior_paid_days=prior_paid_days,
                payment_date=calculation_date,
                statutory_config=statutory_config,
            )
        except ValueError as error:
            raise PayrollConfigurationError(
                f"Invalid SMP input for employee {employee.employee_number}: "
                f"{error}"
            ) from error

        snapshot = {
            "uk_smp_amount": result.amount,
            "uk_smp_salary_withheld": salary_withheld,
            "uk_smp_average_weekly_earnings": result.average_weekly_earnings,
            "uk_smp_higher_weekly_rate": result.higher_weekly_rate,
            "uk_smp_standard_weekly_rate": result.standard_weekly_rate,
            "uk_smp_paid_days": result.payable_days,
            "uk_smp_prior_paid_days": result.prior_paid_days,
            "uk_smp_higher_rate_days": result.higher_rate_days,
            "uk_smp_standard_rate_days": result.standard_rate_days,
            "uk_smp_mpp_start_date": entry.maternity_pay_period_start,
            "uk_smp_eligibility_confirmed": entry.eligibility_confirmed,
            "uk_smp_matb1_received": entry.matb1_received,
        }
        return result.amount, salary_withheld, snapshot

    @staticmethod
    def _uk_spp_history_records(
        employee_id,
        paternity_pay_period_start,
        calculation_date,
    ):
        """Load prior snapshots for the same paternity pay entitlement."""

        return (
            PayrollRecord.query
            .join(PayrollPeriod)
            .filter(
                PayrollRecord.employee_id == employee_id,
                PayrollRecord.uk_spp_ppp_start_date
                == paternity_pay_period_start,
                PayrollPeriod.payment_date < calculation_date,
            )
            .order_by(PayrollPeriod.payment_date.asc())
            .all()
        )

    @classmethod
    def _uk_prior_spp_paid_days(
        cls,
        employee_id,
        paternity_pay_period_start,
        calculation_date,
    ):
        """Return SPP days already paid for this entitlement."""

        return sum(
            int(getattr(row, "uk_spp_paid_days", 0) or 0)
            for row in cls._uk_spp_history_records(
                employee_id,
                paternity_pay_period_start,
                calculation_date,
            )
        )

    @classmethod
    def _uk_spp_snapshot(
        cls,
        *,
        employee,
        period,
        statutory_engine,
        statutory_config,
        calculation_date,
    ):
        """Calculate period SPP input and return pay/snapshot values."""

        entry = PayrollSPPInput.query.filter_by(
            payroll_period_id=period.id,
            employee_id=employee.id,
        ).one_or_none()
        if entry is None:
            return ZERO, ZERO, {}

        if not entry.eligibility_confirmed:
            raise PayrollConfigurationError(
                f"SPP eligibility is not confirmed for employee "
                f"{employee.employee_number}."
            )
        if not entry.declaration_received:
            raise PayrollConfigurationError(
                f"SPP declaration or evidence is not recorded for employee "
                f"{employee.employee_number}."
            )

        contractual_salary = cls._decimal_value(employee.basic_salary)
        salary_withheld = cls._decimal_value(entry.salary_withheld)
        if salary_withheld > contractual_salary:
            raise PayrollConfigurationError(
                "SPP salary withheld cannot exceed the employee's "
                "contractual basic salary."
            )

        prior_paid_days = cls._uk_prior_spp_paid_days(
            employee.id,
            entry.paternity_pay_period_start,
            calculation_date,
        )
        try:
            result = statutory_engine.calculate_statutory_paternity_pay(
                average_weekly_earnings=entry.average_weekly_earnings,
                paid_days=entry.paid_days,
                prior_paid_days=prior_paid_days,
                payment_date=calculation_date,
                statutory_config=statutory_config,
            )
        except ValueError as error:
            raise PayrollConfigurationError(
                f"Invalid SPP input for employee {employee.employee_number}: "
                f"{error}"
            ) from error

        snapshot = {
            "uk_spp_amount": result.amount,
            "uk_spp_salary_withheld": salary_withheld,
            "uk_spp_average_weekly_earnings": result.average_weekly_earnings,
            "uk_spp_weekly_rate": result.weekly_rate,
            "uk_spp_paid_days": result.payable_days,
            "uk_spp_prior_paid_days": result.prior_paid_days,
            "uk_spp_ppp_start_date": entry.paternity_pay_period_start,
            "uk_spp_eligibility_confirmed": entry.eligibility_confirmed,
            "uk_spp_declaration_received": entry.declaration_received,
        }
        return result.amount, salary_withheld, snapshot

    @staticmethod
    def _uk_sap_history_records(employee_id, adoption_pay_period_start, calculation_date):
        return (PayrollRecord.query.join(PayrollPeriod).filter(
            PayrollRecord.employee_id == employee_id,
            PayrollRecord.uk_sap_app_start_date == adoption_pay_period_start,
            PayrollPeriod.payment_date < calculation_date,
        ).order_by(PayrollPeriod.payment_date.asc()).all())

    @classmethod
    def _uk_prior_sap_paid_days(cls, employee_id, adoption_pay_period_start, calculation_date):
        return sum(int(getattr(row, "uk_sap_paid_days", 0) or 0) for row in
                   cls._uk_sap_history_records(employee_id, adoption_pay_period_start, calculation_date))

    @classmethod
    def _uk_sap_snapshot(cls, *, employee, period, statutory_engine, statutory_config, calculation_date):
        """Calculate period SAP and preserve its immutable audit snapshot."""
        entry = PayrollSAPInput.query.filter_by(
            payroll_period_id=period.id, employee_id=employee.id
        ).one_or_none()
        if entry is None:
            return ZERO, ZERO, {}
        if not entry.eligibility_confirmed:
            raise PayrollConfigurationError(f"SAP eligibility is not confirmed for employee {employee.employee_number}.")
        if not entry.adoption_evidence_received:
            raise PayrollConfigurationError(f"SAP adoption evidence is not recorded for employee {employee.employee_number}.")
        salary_withheld = cls._decimal_value(entry.salary_withheld)
        if salary_withheld > cls._decimal_value(employee.basic_salary):
            raise PayrollConfigurationError("SAP salary withheld cannot exceed the employee's contractual basic salary.")
        prior_paid_days = cls._uk_prior_sap_paid_days(
            employee.id, entry.adoption_pay_period_start, calculation_date
        )
        try:
            result = statutory_engine.calculate_statutory_adoption_pay(
                average_weekly_earnings=entry.average_weekly_earnings,
                paid_days=entry.paid_days,
                prior_paid_days=prior_paid_days,
                payment_date=calculation_date,
                statutory_config=statutory_config,
            )
        except ValueError as error:
            raise PayrollConfigurationError(
                f"Invalid SAP input for employee {employee.employee_number}: {error}"
            ) from error
        snapshot = {
            "uk_sap_amount": result.amount,
            "uk_sap_salary_withheld": salary_withheld,
            "uk_sap_average_weekly_earnings": result.average_weekly_earnings,
            "uk_sap_higher_weekly_rate": result.higher_weekly_rate,
            "uk_sap_standard_weekly_rate": result.standard_weekly_rate,
            "uk_sap_paid_days": result.payable_days,
            "uk_sap_prior_paid_days": result.prior_paid_days,
            "uk_sap_higher_rate_days": result.higher_rate_days,
            "uk_sap_standard_rate_days": result.standard_rate_days,
            "uk_sap_app_start_date": entry.adoption_pay_period_start,
            "uk_sap_eligibility_confirmed": entry.eligibility_confirmed,
            "uk_sap_adoption_evidence_received": entry.adoption_evidence_received,
        }
        return result.amount, salary_withheld, snapshot

    @staticmethod
    def _uk_shpp_history_records(employee_id, entitlement_reference, calculation_date):
        return (PayrollRecord.query.join(PayrollPeriod).filter(
            PayrollRecord.employee_id == employee_id,
            PayrollRecord.uk_shpp_entitlement_reference == entitlement_reference,
            PayrollPeriod.payment_date < calculation_date,
        ).order_by(PayrollPeriod.payment_date.asc()).all())

    @classmethod
    def _uk_prior_shpp_paid_days(cls, employee_id, entitlement_reference, calculation_date):
        return sum(int(getattr(row, "uk_shpp_paid_days", 0) or 0) for row in cls._uk_shpp_history_records(employee_id, entitlement_reference, calculation_date))

    @classmethod
    def _uk_shpp_snapshot(cls, *, employee, period, statutory_engine, statutory_config, calculation_date):
        entry = PayrollShPPInput.query.filter_by(payroll_period_id=period.id, employee_id=employee.id).one_or_none()
        if entry is None:
            return ZERO, ZERO, {}
        for valid, message in (
            (entry.eligibility_confirmed, "ShPP eligibility is not confirmed"),
            (entry.curtailment_notice_received, "ShPP curtailment notice is not recorded"),
            (entry.partner_declaration_received, "ShPP partner declaration is not recorded"),
        ):
            if not valid:
                raise PayrollConfigurationError(f"{message} for employee {employee.employee_number}.")
        salary_withheld = cls._decimal_value(entry.salary_withheld)
        if salary_withheld > cls._decimal_value(employee.basic_salary):
            raise PayrollConfigurationError("ShPP salary withheld cannot exceed the employee's contractual basic salary.")
        prior = cls._uk_prior_shpp_paid_days(employee.id, entry.entitlement_reference, calculation_date)
        try:
            result = statutory_engine.calculate_statutory_shared_parental_pay(
                average_weekly_earnings=entry.average_weekly_earnings,
                allocated_days=entry.allocated_days, paid_days=entry.paid_days,
                prior_paid_days=prior, payment_date=calculation_date,
                statutory_config=statutory_config,
            )
        except ValueError as error:
            raise PayrollConfigurationError(f"Invalid ShPP input for employee {employee.employee_number}: {error}") from error
        snapshot = {
            "uk_shpp_amount": result.amount, "uk_shpp_salary_withheld": salary_withheld,
            "uk_shpp_average_weekly_earnings": result.average_weekly_earnings,
            "uk_shpp_weekly_rate": result.weekly_rate, "uk_shpp_allocated_days": result.allocated_days,
            "uk_shpp_paid_days": result.payable_days, "uk_shpp_prior_paid_days": result.prior_paid_days,
            "uk_shpp_remaining_allocated_days": result.remaining_allocated_days,
            "uk_shpp_entitlement_reference": entry.entitlement_reference,
            "uk_shpp_period_start_date": entry.shared_pay_period_start,
            "uk_shpp_eligibility_confirmed": entry.eligibility_confirmed,
            "uk_shpp_curtailment_notice_received": entry.curtailment_notice_received,
            "uk_shpp_partner_declaration_received": entry.partner_declaration_received,
        }
        return result.amount, salary_withheld, snapshot

    @staticmethod
    def _uk_spbp_history_records(
        employee_id, entitlement_reference, calculation_date
    ):
        return (
            PayrollRecord.query.join(PayrollPeriod)
            .filter(
                PayrollRecord.employee_id == employee_id,
                PayrollRecord.uk_spbp_entitlement_reference
                == entitlement_reference,
                PayrollPeriod.payment_date < calculation_date,
            )
            .order_by(PayrollPeriod.payment_date.asc())
            .all()
        )

    @classmethod
    def _uk_prior_spbp_paid_days(
        cls, employee_id, entitlement_reference, calculation_date
    ):
        return sum(
            int(getattr(row, "uk_spbp_paid_days", 0) or 0)
            for row in cls._uk_spbp_history_records(
                employee_id, entitlement_reference, calculation_date
            )
        )

    @classmethod
    def _uk_spbp_snapshot(
        cls,
        *,
        employee,
        period,
        statutory_engine,
        statutory_config,
        calculation_date,
    ):
        entry = PayrollSPBPInput.query.filter_by(
            payroll_period_id=period.id,
            employee_id=employee.id,
        ).one_or_none()
        if entry is None:
            return ZERO, ZERO, {}

        for valid, message in (
            (entry.eligibility_confirmed, "SPBP eligibility is not confirmed"),
            (entry.notice_received, "SPBP notice is not recorded"),
            (entry.declaration_received, "SPBP declaration is not recorded"),
        ):
            if not valid:
                raise PayrollConfigurationError(
                    f"{message} for employee {employee.employee_number}."
                )

        if entry.bereavement_pay_period_start < entry.bereavement_date:
            raise PayrollConfigurationError(
                "SPBP leave cannot start before the bereavement date."
            )
        if (
            entry.bereavement_pay_period_start - entry.bereavement_date
        ).days > 392:
            raise PayrollConfigurationError(
                "SPBP leave must start within 56 weeks of the bereavement date."
            )
        if entry.paid_days and (
            entry.bereavement_pay_period_start
            + timedelta(days=entry.paid_days - 1)
            - entry.bereavement_date
        ).days > 392:
            raise PayrollConfigurationError(
                "SPBP leave must finish within 56 weeks of the bereavement date."
            )

        salary_withheld = cls._decimal_value(entry.salary_withheld)
        if salary_withheld > cls._decimal_value(employee.basic_salary):
            raise PayrollConfigurationError(
                "SPBP salary withheld cannot exceed the employee's "
                "contractual basic salary."
            )

        prior = cls._uk_prior_spbp_paid_days(
            employee.id,
            entry.entitlement_reference,
            calculation_date,
        )
        try:
            result = (
                statutory_engine
                .calculate_statutory_parental_bereavement_pay(
                    average_weekly_earnings=entry.average_weekly_earnings,
                    paid_days=entry.paid_days,
                    prior_paid_days=prior,
                    payment_date=calculation_date,
                    statutory_config=statutory_config,
                )
            )
        except ValueError as error:
            raise PayrollConfigurationError(
                f"Invalid SPBP input for employee "
                f"{employee.employee_number}: {error}"
            ) from error

        snapshot = {
            "uk_spbp_amount": result.amount,
            "uk_spbp_salary_withheld": salary_withheld,
            "uk_spbp_average_weekly_earnings": (
                result.average_weekly_earnings
            ),
            "uk_spbp_weekly_rate": result.weekly_rate,
            "uk_spbp_paid_days": result.payable_days,
            "uk_spbp_prior_paid_days": result.prior_paid_days,
            "uk_spbp_remaining_paid_days": result.remaining_paid_days,
            "uk_spbp_entitlement_reference": entry.entitlement_reference,
            "uk_spbp_bereavement_date": entry.bereavement_date,
            "uk_spbp_period_start_date": entry.bereavement_pay_period_start,
            "uk_spbp_eligibility_confirmed": entry.eligibility_confirmed,
            "uk_spbp_notice_received": entry.notice_received,
            "uk_spbp_declaration_received": entry.declaration_received,
        }
        return result.amount, salary_withheld, snapshot

    @classmethod
    def _uk_ssp_snapshot(
        cls,
        *,
        employee,
        period,
        statutory_engine,
        statutory_config,
        calculation_date,
    ):
        """Calculate period SSP input and return pay/snapshot values."""

        entry = PayrollSSPInput.query.filter_by(
            payroll_period_id=period.id,
            employee_id=employee.id,
        ).one_or_none()
        if entry is None:
            return ZERO, cls._decimal_value(employee.basic_salary), {}

        contractual_salary = cls._decimal_value(employee.basic_salary)
        salary_withheld = cls._decimal_value(entry.salary_withheld)
        if salary_withheld > contractual_salary:
            raise PayrollConfigurationError(
                "SSP salary withheld cannot exceed the employee's "
                "contractual basic salary."
            )

        prior_paid_days = cls._uk_prior_ssp_paid_days(
            employee.id,
            calculation_date,
        )
        try:
            result = statutory_engine.calculate_statutory_sick_pay(
                average_weekly_earnings=entry.average_weekly_earnings,
                qualifying_days_per_week=entry.qualifying_days_per_week,
                qualifying_days_sick=entry.qualifying_days_sick,
                prior_paid_qualifying_days=prior_paid_days,
                sickness_start_date=entry.sickness_start_date,
                statutory_config=statutory_config,
            )
        except ValueError as error:
            raise PayrollConfigurationError(
                f"Invalid SSP input for employee {employee.employee_number}: "
                f"{error}"
            ) from error

        normal_basic_pay = contractual_salary - salary_withheld
        snapshot = {
            "uk_ssp_amount": result.amount,
            "uk_ssp_salary_withheld": salary_withheld,
            "uk_ssp_average_weekly_earnings": result.average_weekly_earnings,
            "uk_ssp_weekly_rate": result.weekly_rate,
            "uk_ssp_qualifying_days_per_week": result.qualifying_days_per_week,
            "uk_ssp_qualifying_days_sick": result.qualifying_days_sick,
            "uk_ssp_payable_days": result.payable_qualifying_days,
            "uk_ssp_prior_paid_days": result.prior_paid_qualifying_days,
            "uk_ssp_sickness_start_date": entry.sickness_start_date,
        }
        return result.amount, normal_basic_pay, snapshot

    @staticmethod
    def _uk_director_appointment_week(employment_date, calculation_date):
        """Return the director's HMRC appointment tax week for this tax year."""

        tax_year_start = date(
            calculation_date.year
            if calculation_date >= date(calculation_date.year, 4, 6)
            else calculation_date.year - 1,
            4,
            6,
        )
        if employment_date is None or employment_date <= tax_year_start:
            return 1
        if employment_date > calculation_date:
            raise PayrollConfigurationError(
                "Director employment date cannot be after the payment date."
            )
        return min(53, ((employment_date - tax_year_start).days // 7) + 1)

    @classmethod
    def _uk_director_final_pay_period(cls, employee, period, calculation_date):
        """Detect the annual or employment-ending director reconciliation."""

        if cls._uk_tax_month(calculation_date) == 12:
            return True
        termination_date = getattr(employee, "termination_date", None)
        return bool(
            termination_date is not None
            and termination_date <= period.end_date
        )

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

        provisional_rule_used = False

        try:
            rule_set = (
                StatutoryRuleService
                .get_applicable_rule_set(
                    calculation_date=calculation_date,
                    currency=currency,
                )
            )

        except StatutoryRuleServiceError as error:
            try:
                rule_set = (
                    StatutoryRuleService
                    .get_latest_prior_year_rule_set(
                        calculation_date=calculation_date,
                        currency=currency,
                    )
                )
                provisional_rule_used = True
            except StatutoryRuleServiceError as fallback_error:
                raise PayrollConfigurationError(
                    "Payroll could not find an applicable "
                    "statutory rule set. "
                    f"Currency: {currency}; calculation date: "
                    f"{calculation_date.isoformat()}. "
                    f"{fallback_error}"
                ) from fallback_error

        try:
            statutory_config = (
                StatutoryRuleService
                .to_configuration(rule_set)
            )
        except StatutoryRuleServiceError as error:
            raise PayrollConfigurationError(str(error)) from error

        return (
            rule_set,
            statutory_config,
            calculation_date,
            provisional_rule_used,
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
            provisional_rule_used,
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

                try:
                    pay_components = cls._recurring_pay_components(
                        employee,
                        calculation_date,
                    )
                    employee_statutory_config = replace(
                        statutory_config,
                        tax_residency=(
                            employee.tax_residency
                            or "Resident"
                        ),
                    )

                    statutory_engine = (
                        StatutoryEngineRegistry
                        .resolve_for_rule_set(
                            rule_set
                        )
                    )

                    calculation_arguments = {
                        "basic_salary": employee.basic_salary,
                        "overtime_amount": ZERO,
                        "allowances_total": pay_components["cash_allowances"],
                        "other_deductions_total": pay_components["net_pay_deductions"],
                        "statutory_config": employee_statutory_config,
                    }

                    uk_snapshot = None
                    uk_ssp_snapshot = {}
                    uk_smp_snapshot = {}
                    uk_spp_snapshot = {}
                    uk_sap_snapshot = {}
                    uk_shpp_snapshot = {}
                    uk_spbp_snapshot = {}
                    persisted_basic_salary = cls._decimal_value(
                        employee.basic_salary
                    )

                    if getattr(statutory_engine, "country_code", None) == "BW":
                        ytd = cls._botswana_ytd_context(
                            employee.id, calculation_date
                        )
                        fixed_current = max(
                            ZERO,
                            cls._decimal_value(employee.basic_salary)
                            + pay_components["taxable_cash_allowances"]
                            + pay_components["non_cash_benefits"]
                            - pay_components["regular_variable_pay"]
                            - pay_components["occasional_irregular_pay"]
                            - pay_components["allowable_deductions"],
                        )
                        calculation_arguments.update({
                            "taxable_allowances_total": pay_components[
                                "taxable_cash_allowances"
                            ],
                            "non_cash_benefits_total": pay_components[
                                "non_cash_benefits"
                            ],
                            "allowable_deductions_total": pay_components[
                                "allowable_deductions"
                            ],
                            "regular_variable_pay_total": pay_components[
                                "regular_variable_pay"
                            ],
                            "occasional_irregular_pay_total": pay_components[
                                "occasional_irregular_pay"
                            ],
                            "ytd_regular_taxable_income": ytd[
                                "regular_taxable_income"
                            ],
                            "ytd_regular_paye": ytd["regular_paye"],
                            "elapsed_payments": ytd["elapsed_payments"],
                            "projected_annual_regular_income": (
                                fixed_current * 12
                                + ytd["regular_variable_income"]
                                + pay_components["regular_variable_pay"]
                            ),
                        })
                    elif getattr(statutory_engine, "country_code", None) == "GB":
                        tax_profile = employee.uk_tax_profile
                        if tax_profile is None:
                            raise PayrollConfigurationError(
                                "The employee does not have a UK tax profile."
                            )
                        ytd = cls._uk_ytd_context(
                            employee.id,
                            calculation_date,
                        )
                        tax_month = cls._uk_tax_month(calculation_date)
                        (
                            ssp_amount,
                            persisted_basic_salary,
                            uk_ssp_snapshot,
                        ) = cls._uk_ssp_snapshot(
                            employee=employee,
                            period=period,
                            statutory_engine=statutory_engine,
                            statutory_config=employee_statutory_config,
                            calculation_date=calculation_date,
                        )
                        statutory_basic_pay = (
                            persisted_basic_salary + ssp_amount
                        )
                        (
                            smp_amount,
                            smp_salary_withheld,
                            uk_smp_snapshot,
                        ) = cls._uk_smp_snapshot(
                            employee=employee,
                            period=period,
                            statutory_engine=statutory_engine,
                            statutory_config=employee_statutory_config,
                            calculation_date=calculation_date,
                        )
                        if smp_salary_withheld > persisted_basic_salary:
                            raise PayrollConfigurationError(
                                "Combined SSP and SMP salary withheld cannot "
                                "exceed contractual basic salary."
                            )
                        persisted_basic_salary -= smp_salary_withheld
                        statutory_basic_pay = (
                            persisted_basic_salary + ssp_amount + smp_amount
                        )
                        (
                            spp_amount,
                            spp_salary_withheld,
                            uk_spp_snapshot,
                        ) = cls._uk_spp_snapshot(
                            employee=employee,
                            period=period,
                            statutory_engine=statutory_engine,
                            statutory_config=employee_statutory_config,
                            calculation_date=calculation_date,
                        )
                        if spp_salary_withheld > persisted_basic_salary:
                            raise PayrollConfigurationError(
                                "Combined SSP, SMP and SPP salary withheld cannot "
                                "exceed contractual basic salary."
                            )
                        persisted_basic_salary -= spp_salary_withheld
                        statutory_basic_pay = (
                            persisted_basic_salary
                            + ssp_amount
                            + smp_amount
                            + spp_amount
                        )
                        sap_amount, sap_salary_withheld, uk_sap_snapshot = cls._uk_sap_snapshot(
                            employee=employee, period=period,
                            statutory_engine=statutory_engine,
                            statutory_config=employee_statutory_config,
                            calculation_date=calculation_date,
                        )
                        if sap_salary_withheld > persisted_basic_salary:
                            raise PayrollConfigurationError(
                                "Combined SSP, SMP, SPP and SAP salary withheld cannot exceed contractual basic salary."
                            )
                        persisted_basic_salary -= sap_salary_withheld
                        statutory_basic_pay = persisted_basic_salary + ssp_amount + smp_amount + spp_amount + sap_amount
                        shpp_amount, shpp_salary_withheld, uk_shpp_snapshot = cls._uk_shpp_snapshot(
                            employee=employee, period=period, statutory_engine=statutory_engine,
                            statutory_config=employee_statutory_config, calculation_date=calculation_date)
                        if shpp_salary_withheld > persisted_basic_salary:
                            raise PayrollConfigurationError("Combined SSP, SMP, SPP, SAP and ShPP salary withheld cannot exceed contractual basic salary.")
                        persisted_basic_salary -= shpp_salary_withheld
                        statutory_basic_pay = persisted_basic_salary + ssp_amount + smp_amount + spp_amount + sap_amount + shpp_amount
                        spbp_amount, spbp_salary_withheld, uk_spbp_snapshot = cls._uk_spbp_snapshot(
                            employee=employee, period=period, statutory_engine=statutory_engine,
                            statutory_config=employee_statutory_config, calculation_date=calculation_date)
                        if spbp_salary_withheld > persisted_basic_salary:
                            raise PayrollConfigurationError("Combined SSP, SMP, SPP, SAP, ShPP and SPBP salary withheld cannot exceed contractual basic salary.")
                        persisted_basic_salary -= spbp_salary_withheld
                        statutory_basic_pay = persisted_basic_salary + ssp_amount + smp_amount + spp_amount + sap_amount + shpp_amount + spbp_amount
                        calculation_arguments["basic_salary"] = statutory_basic_pay
                        current_taxable_pay = max(
                            ZERO,
                            statutory_basic_pay
                            + pay_components["taxable_cash_allowances"]
                            + pay_components["non_cash_benefits"]
                            - pay_components["allowable_deductions"],
                        )
                        calculation_arguments.update({
                            "taxable_allowances_total": pay_components[
                                "taxable_cash_allowances"
                            ],
                            "non_cash_benefits_total": pay_components[
                                "non_cash_benefits"
                            ],
                            "allowable_deductions_total": pay_components[
                                "allowable_deductions"
                            ],
                            "tax_profile": tax_profile,
                            "tax_month": tax_month,
                            "prior_taxable_pay": ytd["taxable_pay"],
                            "prior_tax_paid": ytd["tax_paid"],
                        })
                        if bool(getattr(tax_profile, "is_director", False)):
                            calculation_arguments.update({
                                "prior_ni_earnings": ytd["ni_earnings"],
                                "prior_employee_ni": ytd["employee_ni"],
                                "prior_employer_ni": ytd["employer_ni"],
                                "director_appointment_week": (
                                    cls._uk_director_appointment_week(
                                        employee.employment_date,
                                        calculation_date,
                                    )
                                ),
                                "director_final_pay_period": (
                                    cls._uk_director_final_pay_period(
                                        employee,
                                        period,
                                        calculation_date,
                                    )
                                ),
                            })
                        uk_snapshot = {
                            "uk_tax_code": tax_profile.tax_code,
                            "uk_tax_basis": tax_profile.tax_basis,
                            "uk_tax_region": tax_profile.tax_region,
                            "uk_tax_month": tax_month,
                            "uk_taxable_pay": current_taxable_pay,
                            "uk_prior_taxable_pay": ytd["taxable_pay"],
                            "uk_prior_tax_paid": ytd["tax_paid"],
                        }

                    calculation = statutory_engine.calculate(
                        **calculation_arguments
                    )

                except (
                    StatutoryEngineRegistryError,
                    StatutoryEngineError,
                ) as error:
                    raise PayrollConfigurationError(
                        (
                            "Payroll could not resolve the "
                            "configured statutory engine. "
                            f"{error}"
                        )
                    ) from error

                payroll_record = PayrollRecord(
                    payroll_period_id=period.id,
                    employee_id=employee.id,
                    processed_by=processed_by_user_id,

                    basic_salary=(
                        persisted_basic_salary
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

                    regular_paye=calculation.regular_paye,

                    irregular_paye=calculation.irregular_paye,

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

                    **(uk_snapshot or {}),
                    **uk_ssp_snapshot,
                    **uk_smp_snapshot,
                    **uk_spp_snapshot,
                    **uk_sap_snapshot,
                    **uk_shpp_snapshot,
                    **uk_spbp_snapshot,
                )

                db.session.add(payroll_record)

                for assignment, definition, amount in pay_components[
                    "allowance_lines"
                ]:
                    payroll_record.allowances.append(Allowance(
                        employee_id=employee.id,
                        allowance_type=definition.name,
                        amount=amount,
                        description=assignment.notes or definition.description,
                        earning_classification=definition.earning_classification,
                        is_taxable=definition.is_taxable,
                    ))

                for assignment, definition, amount in pay_components[
                    "deduction_lines"
                ]:
                    payroll_record.deductions.append(Deduction(
                        employee_id=employee.id,
                        deduction_type=definition.name,
                        amount=amount,
                        description=assignment.notes or definition.description,
                        is_tax_deductible=definition.is_tax_deductible,
                        reduces_net_pay=definition.reduces_net_pay,
                    ))

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
                    + (
                        " PROVISIONAL FALLBACK: prior-year statutory "
                        "rates were used because no verified current-year "
                        "rule was available."
                        if provisional_rule_used
                        else ""
                    )
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
            provisional_rule_used=provisional_rule_used,
            rule_effective_to=rule_set.effective_to,
        )
