from datetime import datetime

from app.extensions import db


class Allowance(db.Model):
    """Stores an additional earning linked to a payroll record."""

    __tablename__ = "allowances"

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

    allowance_type = db.Column(
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
        back_populates="allowances",
    )

    employee = db.relationship(
        "Employee",
        back_populates="allowances",
    )

    __table_args__ = (
        db.CheckConstraint(
            "amount >= 0",
            name="ck_allowance_amount_non_negative",
        ),
    )

    def __repr__(self):
        return (
            f"<Allowance {self.allowance_type}: "
            f"{self.amount}>"
        )
