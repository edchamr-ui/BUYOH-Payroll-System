"""Payroll processing and register service."""

from dataclasses import dataclass, replace
from datetime import date, datetime
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
