from datetime import datetime
from app.extensions import db


class PayrollShPPInput(db.Model):
    """Period-specific UK Shared Parental Pay allocation and evidence."""
    __tablename__ = "payroll_shpp_inputs"
    id = db.Column(db.Integer, primary_key=True)
    payroll_period_id = db.Column(db.Integer, db.ForeignKey("payroll_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    entitlement_reference = db.Column(db.String(80), nullable=False, index=True)
    shared_pay_period_start = db.Column(db.Date, nullable=False)
    average_weekly_earnings = db.Column(db.Numeric(12, 2), nullable=False)
    allocated_days = db.Column(db.Integer, nullable=False)
    paid_days = db.Column(db.Integer, nullable=False)
    salary_withheld = db.Column(db.Numeric(12, 2), nullable=False, default=0, server_default="0")
    eligibility_confirmed = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    curtailment_notice_received = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    partner_declaration_received = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint("payroll_period_id", "employee_id", name="uq_payroll_shpp_input_period_employee"),
        db.CheckConstraint("average_weekly_earnings >= 0", name="ck_payroll_shpp_input_awe_non_negative"),
        db.CheckConstraint("allocated_days >= 0 AND allocated_days <= 259", name="ck_payroll_shpp_input_allocated_days"),
        db.CheckConstraint("paid_days >= 0", name="ck_payroll_shpp_input_paid_days_non_negative"),
        db.CheckConstraint("salary_withheld >= 0", name="ck_payroll_shpp_input_salary_withheld_non_negative"),
    )
