from datetime import datetime

from app.extensions import db


class PayrollRecord(db.Model):
    """Stores one employee's payroll calculation for one payroll period."""

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

    paye = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
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
            "total_deductions >= 0",
            name="ck_payroll_record_deductions_non_negative",
        ),
        db.CheckConstraint(
            "net_pay >= 0",
            name="ck_payroll_record_net_pay_non_negative",
        ),
    )

    def __repr__(self):
        return (
            f"<PayrollRecord period={self.payroll_period_id} "
            f"employee={self.employee_id}>"
        )
