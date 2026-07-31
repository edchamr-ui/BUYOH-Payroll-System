"""Recurring employee allowance assignments."""

from datetime import datetime

from app.extensions import db


class EmployeeAllowance(db.Model):
    """
    Assign a reusable allowance type to an employee.

    Payroll processing will later read active assignments and
    copy the calculated values into the historical allowances
    table for each payroll record.
    """

    __tablename__ = "employee_allowances"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

    allowance_type_id = db.Column(
        db.Integer,
        db.ForeignKey("allowance_types.id"),
        nullable=False,
        index=True,
    )

    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    percentage = db.Column(
        db.Numeric(7, 4),
        nullable=False,
        default=0,
        server_default="0",
    )

    start_date = db.Column(
        db.Date,
        nullable=True,
    )

    end_date = db.Column(
        db.Date,
        nullable=True,
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
        index=True,
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    employee = db.relationship(
        "Employee",
        back_populates="recurring_allowances",
    )

    allowance_type = db.relationship(
        "AllowanceType",
        back_populates="employee_allowances",
    )

    creator = db.relationship(
        "User",
        foreign_keys=[created_by],
    )

    __table_args__ = (
        db.UniqueConstraint(
            "employee_id",
            "allowance_type_id",
            name=(
                "uq_employee_allowance_employee_type"
            ),
        ),
        db.CheckConstraint(
            "amount >= 0",
            name=(
                "ck_employee_allowance_amount_non_negative"
            ),
        ),
        db.CheckConstraint(
            "percentage >= 0",
            name=(
                "ck_employee_allowance_percentage_non_negative"
            ),
        ),
        db.CheckConstraint(
            (
                "end_date IS NULL "
                "OR start_date IS NULL "
                "OR end_date >= start_date"
            ),
            name=(
                "ck_employee_allowance_valid_date_range"
            ),
        ),
    )

    def __repr__(self):
        return (
            f"<EmployeeAllowance "
            f"employee={self.employee_id} "
            f"type={self.allowance_type_id}>"
        )

