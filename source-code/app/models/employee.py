from datetime import datetime

from app.extensions import db


class Employee(db.Model):
    """Stores employee master records used during payroll processing."""

    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=False,
        index=True,
    )

    employee_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    first_name = db.Column(
        db.String(100),
        nullable=False,
    )

    last_name = db.Column(
        db.String(100),
        nullable=False,
    )

    national_id = db.Column(
        db.String(50),
        unique=True,
        nullable=True,
    )

    job_title = db.Column(
        db.String(100),
        nullable=False,
    )

    employment_date = db.Column(
        db.Date,
        nullable=False,
    )

    termination_date = db.Column(
        db.Date,
        nullable=True,
    )

    basic_salary = db.Column(
        db.Numeric(12, 2),
        nullable=False,
    )

    employment_status = db.Column(
        db.String(30),
        nullable=False,
        default="Active",
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
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

    department = db.relationship(
        "Department",
        back_populates="employees",
    )

    payroll_records = db.relationship(
    "PayrollRecord",
    back_populates="employee",
    lazy="select",
    )

    allowances = db.relationship(
    "Allowance",
    back_populates="employee",
    lazy="select",
    )

    deductions = db.relationship(
    "Deduction",
    back_populates="employee",
    lazy="select",
    )

    generated_payslips = db.relationship(
    "Payslip",
    back_populates="generator",
    lazy="select",
    )

    def __repr__(self):
        return (
            f"<Employee {self.employee_number}: "
            f"{self.first_name} {self.last_name}>"
        )
