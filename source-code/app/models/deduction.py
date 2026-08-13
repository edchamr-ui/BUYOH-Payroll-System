from datetime import datetime

from app.extensions import db
from app.time_utils import legacy_utc_now


class Deduction(db.Model):
    """Stores a deduction linked to a payroll record."""

    __tablename__ = "deductions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    payroll_record_id = db.Column(
        db.Integer,
        db.ForeignKey("payroll_records.id"),
        nullable=False,
        index=True,
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

    deduction_type = db.Column(
        db.String(100),
        nullable=False,
    )

    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    is_tax_deductible = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    reduces_net_pay = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=legacy_utc_now,
    )

    payroll_record = db.relationship(
        "PayrollRecord",
        back_populates="deductions",
    )

    employee = db.relationship(
        "Employee",
        back_populates="deductions",
    )

    __table_args__ = (
        db.CheckConstraint(
            "amount >= 0",
            name="ck_deduction_amount_non_negative",
        ),
    )

    def __repr__(self):
        return (
            f"<Deduction {self.deduction_type}: "
            f"{self.amount}>"
        )
