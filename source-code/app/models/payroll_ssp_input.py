from datetime import datetime

from app.extensions import db


class PayrollSSPInput(db.Model):
    """Period-specific UK Statutory Sick Pay input."""

    __tablename__ = "payroll_ssp_inputs"

    id = db.Column(db.Integer, primary_key=True)
    payroll_period_id = db.Column(
        db.Integer,
        db.ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sickness_start_date = db.Column(db.Date, nullable=False)
    average_weekly_earnings = db.Column(db.Numeric(12, 2), nullable=False)
    qualifying_days_per_week = db.Column(db.Integer, nullable=False)
    qualifying_days_sick = db.Column(db.Integer, nullable=False)
    salary_withheld = db.Column(
        db.Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "payroll_period_id",
            "employee_id",
            name="uq_payroll_ssp_input_period_employee",
        ),
        db.CheckConstraint(
            "average_weekly_earnings >= 0",
            name="ck_payroll_ssp_input_awe_non_negative",
        ),
        db.CheckConstraint(
            "qualifying_days_per_week BETWEEN 1 AND 7",
            name="ck_payroll_ssp_input_days_per_week",
        ),
        db.CheckConstraint(
            "qualifying_days_sick >= 0",
            name="ck_payroll_ssp_input_sick_days_non_negative",
        ),
        db.CheckConstraint(
            "salary_withheld >= 0",
            name="ck_payroll_ssp_input_salary_withheld_non_negative",
        ),
    )

