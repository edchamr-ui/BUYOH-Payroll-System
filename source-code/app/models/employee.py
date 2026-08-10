"""Employee database model."""

from datetime import datetime

from app.extensions import db


class Employee(db.Model):
    """Store employee master information."""

    __tablename__ = "employees"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

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

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=True,
        index=True,
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

    tax_residency = db.Column(
        db.String(20),
        nullable=False,
        default="Resident",
        server_default="Resident",
        index=True,
    )

    payment_method = db.Column(
        db.String(30),
        nullable=False,
        default="Cash",
        server_default="Cash",
    )

    bank_name = db.Column(
        db.String(100),
        nullable=True,
    )

    bank_branch = db.Column(
        db.String(100),
        nullable=True,
    )

    bank_code = db.Column(
        db.String(20),
        nullable=True,
    )

    account_name = db.Column(
        db.String(150),
        nullable=True,
    )

    account_number = db.Column(
        db.String(50),
        nullable=True,
    )

    account_type = db.Column(
        db.String(20),
        nullable=True,
    )

    employment_status = db.Column(
        db.String(30),
        nullable=False,
        default="Active",
        server_default="Active",
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
        index=True,
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

    payslips = db.relationship(
        "Payslip",
        back_populates="employee",
        lazy="select",
    )

    recurring_allowances = db.relationship(
        "EmployeeAllowance",
        back_populates="employee",
        lazy="select",
        cascade="all, delete-orphan",
    )

    recurring_deductions = db.relationship(
        "EmployeeDeduction",
        back_populates="employee",
        lazy="select",
        cascade="all, delete-orphan",
    )

    uk_tax_profile = db.relationship(
        "EmployeeUKTaxProfile",
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def full_name(self):
        """Return the employee's full display name."""

        return (
            f"{self.first_name} {self.last_name}"
        ).strip()

    def __repr__(self):
        return (
            f"<Employee {self.employee_number}: "
            f"{self.full_name}>"
        )
