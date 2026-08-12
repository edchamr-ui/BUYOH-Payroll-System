"""United Kingdom statutory payroll engine for tax year 2026/27."""

from decimal import Decimal

from app.services.payroll_calculator import PayrollCalculation, money
from app.services.statutory_engines.base import (
    BaseStatutoryEngine,
    InvalidStatutoryConfigurationError,
    StatutoryEngineValidation,
)
from app.services.statutory_engines.uk_paye import (
    calculate_monthly_paye_from_profile,
)
from app.services.statutory_engines.uk_ni import (
    calculate_director_class_1,
    calculate_monthly_class_1,
)
from app.services.statutory_engines.uk_ssp import calculate_ssp_2026_27
from app.services.statutory_engines.uk_smp import calculate_smp_2026_27
from app.services.statutory_engines.uk_spp import calculate_spp_2026_27


ZERO = Decimal("0.00")


class UKStatutoryEngine(BaseStatutoryEngine):
    """HMRC-compatible monthly PAYE and Class 1 NI engine."""

    engine_key = "UK_PAYE"
    country_code = "GB"
    aliases = (
        "UK",
        "GB",
        "GBR",
        "GB_PAYE",
    )

    contribution_labels = {
        "employee": "Employee National Insurance",
        "employer": "Employer National Insurance",
        "levy": "Payroll Levy",
    }

    @classmethod
    def validate_configuration(cls, statutory_config):
        """Validate the rule-set values needed by the UK PAYE engine."""

        errors = []
        warnings = []

        if statutory_config is None:
            errors.append("A statutory configuration is required.")
        else:
            currency = str(
                getattr(statutory_config, "currency", "") or ""
            ).strip().upper()

            if currency != "GBP":
                errors.append("UK PAYE engine requires GBP currency.")

            if not bool(getattr(statutory_config, "paye_enabled", False)):
                errors.append("UK PAYE must be enabled.")

            if tuple(getattr(statutory_config, "tax_bands", ()) or ()):
                warnings.append(
                    "Configured tax bands are ignored because UK PAYE uses "
                    "the HMRC 2026/27 routine parameters."
                )

        return StatutoryEngineValidation(
            engine_key=cls.engine_key,
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @classmethod
    def _require_valid_configuration(cls, statutory_config):
        validation = cls.validate_configuration(statutory_config)

        if not validation.valid:
            raise InvalidStatutoryConfigurationError(
                "; ".join(validation.errors)
            )

    def calculate_paye(
        self,
        *,
        taxable_income,
        statutory_config,
        tax_profile=None,
        tax_month=None,
        prior_taxable_pay=ZERO,
        prior_tax_paid=ZERO,
        current_pay_for_regulatory_limit=None,
        payrolled_benefits=ZERO,
    ):
        """Calculate one month's PAYE and return its auditable result."""

        self._require_valid_configuration(statutory_config)

        return calculate_monthly_paye_from_profile(
            tax_profile=tax_profile,
            current_taxable_pay=taxable_income,
            tax_month=tax_month,
            prior_taxable_pay=prior_taxable_pay,
            prior_tax_paid=prior_tax_paid,
            current_pay_for_regulatory_limit=(
                current_pay_for_regulatory_limit
            ),
            payrolled_benefits=payrolled_benefits,
        )

    def calculate_statutory_sick_pay(
        self,
        *,
        average_weekly_earnings,
        qualifying_days_per_week,
        qualifying_days_sick,
        prior_paid_qualifying_days=0,
        sickness_start_date=None,
        statutory_config=None,
    ):
        """Return an auditable 2026/27 Statutory Sick Pay result."""

        self._require_valid_configuration(statutory_config)
        return calculate_ssp_2026_27(
            average_weekly_earnings=average_weekly_earnings,
            qualifying_days_per_week=qualifying_days_per_week,
            qualifying_days_sick=qualifying_days_sick,
            prior_paid_qualifying_days=prior_paid_qualifying_days,
            sickness_start_date=sickness_start_date,
        )

    def calculate_statutory_maternity_pay(
        self,
        *,
        average_weekly_earnings,
        paid_days,
        prior_paid_days=0,
        payment_date=None,
        statutory_config=None,
    ):
        """Return an auditable 2026/27 Statutory Maternity Pay result."""

        self._require_valid_configuration(statutory_config)
        return calculate_smp_2026_27(
            average_weekly_earnings=average_weekly_earnings,
            paid_days=paid_days,
            prior_paid_days=prior_paid_days,
            payment_date=payment_date,
        )

    def calculate_statutory_paternity_pay(
        self,
        *,
        average_weekly_earnings,
        paid_days,
        prior_paid_days=0,
        payment_date=None,
        statutory_config=None,
    ):
        """Return an auditable 2026/27 Statutory Paternity Pay result."""

        self._require_valid_configuration(statutory_config)
        return calculate_spp_2026_27(
            average_weekly_earnings=average_weekly_earnings,
            paid_days=paid_days,
            prior_paid_days=prior_paid_days,
            payment_date=payment_date,
        )

    def calculate(
        self,
        *,
        basic_salary,
        overtime_amount,
        allowances_total,
        other_deductions_total,
        statutory_config,
        taxable_allowances_total=None,
        non_cash_benefits_total=ZERO,
        allowable_deductions_total=ZERO,
        tax_profile=None,
        tax_month=None,
        prior_taxable_pay=ZERO,
        prior_tax_paid=ZERO,
        current_pay_for_regulatory_limit=None,
        prior_ni_earnings=ZERO,
        prior_employee_ni=ZERO,
        prior_employer_ni=ZERO,
        director_appointment_week=1,
        director_final_pay_period=False,
    ):
        """Return the application's backward-compatible payroll result."""

        self._require_valid_configuration(statutory_config)

        basic = money(basic_salary)
        overtime = money(overtime_amount)
        allowances = money(allowances_total)
        taxable_allowances = money(
            allowances_total
            if taxable_allowances_total is None
            else taxable_allowances_total
        )
        benefits = money(non_cash_benefits_total)
        allowable_deductions = money(allowable_deductions_total)
        other_deductions = money(other_deductions_total)

        values = {
            "Basic salary": basic,
            "Overtime amount": overtime,
            "Allowances": allowances,
            "Taxable allowances": taxable_allowances,
            "Non-cash benefits": benefits,
            "Allowable deductions": allowable_deductions,
            "Other deductions": other_deductions,
        }

        for field_name, value in values.items():
            if value < ZERO:
                raise ValueError(f"{field_name} cannot be negative.")

        gross_pay = money(basic + overtime + allowances)
        taxable_income = money(max(
            ZERO,
            basic
            + overtime
            + taxable_allowances
            + benefits
            - allowable_deductions,
        ))
        regulatory_limit_pay = (
            money(
                basic
                + overtime
                + taxable_allowances
                + benefits
            )
            if current_pay_for_regulatory_limit is None
            else money(current_pay_for_regulatory_limit)
        )

        paye_result = self.calculate_paye(
            taxable_income=taxable_income,
            statutory_config=statutory_config,
            tax_profile=tax_profile,
            tax_month=tax_month,
            prior_taxable_pay=prior_taxable_pay,
            prior_tax_paid=prior_tax_paid,
            current_pay_for_regulatory_limit=regulatory_limit_pay,
            payrolled_benefits=benefits,
        )
        paye = money(paye_result.paye)
        ni_category = getattr(tax_profile, "ni_category", "A")
        if bool(getattr(tax_profile, "is_director", False)):
            ni_result = calculate_director_class_1(
                gross_pay,
                category=ni_category,
                method=getattr(
                    tax_profile,
                    "director_ni_method",
                    "STANDARD",
                ),
                appointment_week=director_appointment_week,
                prior_earnings=prior_ni_earnings,
                prior_employee_ni=prior_employee_ni,
                prior_employer_ni=prior_employer_ni,
                final_pay_period=director_final_pay_period,
            )
        else:
            ni_result = calculate_monthly_class_1(
                gross_pay,
                ni_category,
            )
        employee_ni = money(ni_result.employee_ni)
        employer_ni = money(ni_result.employer_ni)
        total_deductions = money(
            paye + employee_ni + other_deductions
        )
        net_pay = money(gross_pay - total_deductions)

        if net_pay < ZERO:
            raise ValueError("Payroll deductions cannot exceed gross pay.")

        return PayrollCalculation(
            basic_salary=basic,
            overtime_amount=overtime,
            allowances_total=allowances,
            non_cash_benefits_total=benefits,
            allowable_deductions_total=allowable_deductions,
            gross_pay=gross_pay,
            nssa=employee_ni,
            employer_nssa=employer_ni,
            paye=paye,
            regular_paye=paye,
            irregular_paye=ZERO,
            aids_levy=ZERO,
            other_deductions_total=other_deductions,
            total_deductions=total_deductions,
            net_pay=net_pay,
            employer_cost=money(gross_pay + employer_ni),
        )

    def calculate_employee_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
        ni_category="A",
    ):
        """Return the employee Class 1 NI contribution."""

        self._require_valid_configuration(statutory_config)
        result = calculate_monthly_class_1(
            gross_pay,
            ni_category,
        )
        return {
            self.contribution_labels["employee"]: result.employee_ni,
        }

    def calculate_employer_contributions(
        self,
        *,
        gross_pay,
        statutory_config,
        ni_category="A",
    ):
        """Return the employer Class 1 NI contribution."""

        self._require_valid_configuration(statutory_config)
        result = calculate_monthly_class_1(
            gross_pay,
            ni_category,
        )
        return {
            self.contribution_labels["employer"]: result.employer_ni,
        }

    def calculate_levies(
        self,
        *,
        paye,
        gross_pay,
        statutory_config,
    ):
        """No payroll levy is applied by the PAYE-only checkpoint."""

        self._require_valid_configuration(statutory_config)
        return {}
