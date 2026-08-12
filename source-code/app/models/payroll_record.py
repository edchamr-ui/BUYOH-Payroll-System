from datetime import datetime

from app.extensions import db


class PayrollRecord(db.Model):
    """Stores one employee payroll calculation for one period."""

    __tablename__ = "payroll_records"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    payroll_period_id = db.Column(
        db.Integer,
        db.ForeignKey("payroll_periods.id"),
        nullable=False,
        index=True,
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

    processed_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
    )

    basic_salary = db.Column(
        db.Numeric(12, 2),
        nullable=False,
    )

    overtime_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
    )

    allowances_total = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
    )

    gross_pay = db.Column(
        db.Numeric(12, 2),
        nullable=False,
    )

    nssa = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
    )

    employer_nssa = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
    )

    paye = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
    )

    uk_tax_code = db.Column(db.String(20), nullable=True)

    uk_tax_basis = db.Column(db.String(20), nullable=True)

    uk_tax_region = db.Column(db.String(20), nullable=True)

    uk_tax_month = db.Column(db.Integer, nullable=True)

    uk_taxable_pay = db.Column(
        db.Numeric(14, 2),
        nullable=True,
    )

    uk_prior_taxable_pay = db.Column(
        db.Numeric(14, 2),
        nullable=True,
    )

    uk_prior_tax_paid = db.Column(
        db.Numeric(14, 2),
        nullable=True,
    )

    uk_ssp_amount = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )

    uk_ssp_salary_withheld = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )

    uk_ssp_average_weekly_earnings = db.Column(db.Numeric(12, 2))
    uk_ssp_weekly_rate = db.Column(db.Numeric(12, 2))
    uk_ssp_qualifying_days_per_week = db.Column(db.Integer)
    uk_ssp_qualifying_days_sick = db.Column(db.Integer)
    uk_ssp_payable_days = db.Column(db.Integer)
    uk_ssp_prior_paid_days = db.Column(db.Integer)
    uk_ssp_sickness_start_date = db.Column(db.Date)

    uk_smp_amount = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    uk_smp_salary_withheld = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    uk_smp_average_weekly_earnings = db.Column(db.Numeric(12, 2))
    uk_smp_higher_weekly_rate = db.Column(db.Numeric(12, 2))
    uk_smp_standard_weekly_rate = db.Column(db.Numeric(12, 2))
    uk_smp_paid_days = db.Column(db.Integer)
    uk_smp_prior_paid_days = db.Column(db.Integer)
    uk_smp_higher_rate_days = db.Column(db.Integer)
    uk_smp_standard_rate_days = db.Column(db.Integer)
    uk_smp_mpp_start_date = db.Column(db.Date)
    uk_smp_eligibility_confirmed = db.Column(db.Boolean)
    uk_smp_matb1_received = db.Column(db.Boolean)

    uk_spp_amount = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    uk_spp_salary_withheld = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    uk_spp_average_weekly_earnings = db.Column(db.Numeric(12, 2))
    uk_spp_weekly_rate = db.Column(db.Numeric(12, 2))
    uk_spp_paid_days = db.Column(db.Integer)
    uk_spp_prior_paid_days = db.Column(db.Integer)
    uk_spp_ppp_start_date = db.Column(db.Date)
    uk_spp_eligibility_confirmed = db.Column(db.Boolean)
    uk_spp_declaration_received = db.Column(db.Boolean)

    regular_paye = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )

    irregular_paye = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )

    aids_levy = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
    )

    other_deductions_total = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
    )

    total_deductions = db.Column(
        db.Numeric(12, 2),
        nullable=False,
    )

    net_pay = db.Column(
        db.Numeric(12, 2),
        nullable=False,
    )

    employer_cost = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Draft",
    )

    processed_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    payroll_period = db.relationship(
        "PayrollPeriod",
        back_populates="payroll_records",
    )

    employee = db.relationship(
        "Employee",
        back_populates="payroll_records",
    )

    processor = db.relationship(
        "User",
        back_populates="processed_payroll_records",
    )

    allowances = db.relationship(
        "Allowance",
        back_populates="payroll_record",
        lazy="select",
        cascade="all, delete-orphan",
    )

    deductions = db.relationship(
        "Deduction",
        back_populates="payroll_record",
        lazy="select",
        cascade="all, delete-orphan",
    )

    payslip = db.relationship(
        "Payslip",
        back_populates="payroll_record",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "payroll_period_id",
            "employee_id",
            name="uq_payroll_record_period_employee",
        ),
        db.CheckConstraint(
            "basic_salary >= 0",
            name="ck_payroll_record_basic_salary_non_negative",
        ),
        db.CheckConstraint(
            "overtime_amount >= 0",
            name="ck_payroll_record_overtime_non_negative",
        ),
        db.CheckConstraint(
            "allowances_total >= 0",
            name="ck_payroll_record_allowances_non_negative",
        ),
        db.CheckConstraint(
            "nssa >= 0",
            name="ck_payroll_record_nssa_non_negative",
        ),
        db.CheckConstraint(
            "employer_nssa >= 0",
            name="ck_payroll_record_employer_nssa_non_negative",
        ),
        db.CheckConstraint(
            "uk_tax_month IS NULL OR "
            "(uk_tax_month >= 1 AND uk_tax_month <= 12)",
            name="ck_payroll_record_uk_tax_month_valid",
        ),
        db.CheckConstraint(
            "uk_taxable_pay IS NULL OR uk_taxable_pay >= 0",
            name="ck_payroll_record_uk_taxable_pay_non_negative",
        ),
        db.CheckConstraint(
            "uk_ssp_amount >= 0 AND uk_ssp_salary_withheld >= 0",
            name="ck_payroll_record_uk_ssp_amounts_non_negative",
        ),
        db.CheckConstraint(
            "uk_smp_amount >= 0 AND uk_smp_salary_withheld >= 0",
            name="ck_payroll_record_uk_smp_amounts_non_negative",
        ),
        db.CheckConstraint(
            "uk_spp_amount >= 0 AND uk_spp_salary_withheld >= 0",
            name="ck_payroll_record_uk_spp_amounts_non_negative",
        ),
        db.CheckConstraint(
            "total_deductions >= 0",
            name="ck_payroll_record_deductions_non_negative",
        ),
        db.CheckConstraint(
            "net_pay >= 0",
            name="ck_payroll_record_net_pay_non_negative",
        ),
        db.CheckConstraint(
            "employer_cost >= 0",
            name="ck_payroll_record_employer_cost_non_negative",
        ),
    )

    def __repr__(self):
        return (
            f"<PayrollRecord period={self.payroll_period_id} "
            f"employee={self.employee_id}>"
        )
