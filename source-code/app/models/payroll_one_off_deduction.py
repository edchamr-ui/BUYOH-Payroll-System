"""Draft-period one-off employee deductions."""

from decimal import Decimal, ROUND_HALF_UP

from app.extensions import db
from app.time_utils import legacy_utc_now


class PayrollOneOffDeduction(db.Model):
    """A non-recurring deduction belonging to one payroll period."""

    __tablename__ = "payroll_one_off_deductions"

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
    deduction_type = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(300))
    priority = db.Column(db.Integer, nullable=False, default=100)
    allow_partial = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="Draft")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(
        db.DateTime, nullable=False, default=legacy_utc_now
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=legacy_utc_now,
        onupdate=legacy_utc_now,
    )

    payroll_period = db.relationship("PayrollPeriod")
    employee = db.relationship("Employee")
    creator = db.relationship("User", foreign_keys=[created_by])
    approver = db.relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        db.CheckConstraint(
            "amount > 0", name="ck_one_off_deduction_amount_positive"
        ),
        db.CheckConstraint(
            "priority >= 0", name="ck_one_off_deduction_priority_non_negative"
        ),
        db.CheckConstraint(
            "status IN ('Draft', 'Approved')",
            name="ck_one_off_deduction_status_valid",
        ),
        db.Index(
            "ix_one_off_deduction_period_employee",
            "payroll_period_id",
            "employee_id",
        ),
    )

    @staticmethod
    def money(value):
        amount = Decimal(str(value)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if amount <= 0:
            raise ValueError("A one-off deduction must be greater than zero.")
        return amount
