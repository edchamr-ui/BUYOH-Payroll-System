from datetime import datetime

from app.extensions import db


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

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
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
