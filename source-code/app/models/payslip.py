from datetime import datetime

from app.extensions import db


class Payslip(db.Model):
    """Stores metadata for a generated employee payslip."""

    __tablename__ = "payslips"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    payroll_record_id = db.Column(
        db.Integer,
        db.ForeignKey("payroll_records.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

    generated_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
    )

    file_path = db.Column(
        db.Text,
        nullable=False,
    )

    generated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    payroll_record = db.relationship(
        "PayrollRecord",
        back_populates="payslip",
    )

    employee = db.relationship(
        "Employee",
        back_populates="payslips",
    )

    generator = db.relationship(
        "User",
        back_populates="generated_payslips",
    )

    def __repr__(self):
        return (
            f"<Payslip payroll_record={self.payroll_record_id} "
            f"employee={self.employee_id}>"
        )

