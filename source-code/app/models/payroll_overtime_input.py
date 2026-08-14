"""Draft-period overtime inputs."""

from decimal import Decimal, ROUND_HALF_UP

from app.extensions import db
from app.time_utils import legacy_utc_now


MONEY = Decimal("0.01")


class PayrollOvertimeInput(db.Model):
    """Auditable overtime entered for one employee and payroll period."""

    __tablename__ = "payroll_overtime_inputs"

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
    category = db.Column(db.String(80), nullable=False, default="Ordinary")
    work_date = db.Column(db.Date)
    hours = db.Column(db.Numeric(10, 2), nullable=False)
    hourly_rate = db.Column(db.Numeric(12, 4), nullable=False)
    multiplier = db.Column(db.Numeric(7, 4), nullable=False, default=1)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(300))
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
        db.CheckConstraint("hours > 0", name="ck_overtime_hours_positive"),
        db.CheckConstraint(
            "hourly_rate >= 0", name="ck_overtime_rate_non_negative"
        ),
        db.CheckConstraint(
            "multiplier > 0", name="ck_overtime_multiplier_positive"
        ),
        db.CheckConstraint(
            "amount >= 0", name="ck_overtime_amount_non_negative"
        ),
        db.CheckConstraint(
            "status IN ('Draft', 'Approved')",
            name="ck_overtime_status_valid",
        ),
        db.Index(
            "ix_overtime_period_employee",
            "payroll_period_id",
            "employee_id",
        ),
    )

    @staticmethod
    def calculate_amount(hours, hourly_rate, multiplier):
        """Return a money-rounded overtime amount."""

        values = tuple(
            Decimal(str(value)) for value in (hours, hourly_rate, multiplier)
        )
        if values[0] <= 0:
            raise ValueError("Overtime hours must be greater than zero.")
        if values[1] < 0:
            raise ValueError("The overtime hourly rate cannot be negative.")
        if values[2] <= 0:
            raise ValueError("The overtime multiplier must be greater than zero.")
        return (values[0] * values[1] * values[2]).quantize(
            MONEY, rounding=ROUND_HALF_UP
        )

    def recalculate(self):
        self.amount = self.calculate_amount(
            self.hours, self.hourly_rate, self.multiplier
        )
        return self.amount
