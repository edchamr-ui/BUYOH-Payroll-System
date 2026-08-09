"""Reusable deduction-type definitions."""

from datetime import datetime

from app.extensions import db


class DeductionType(db.Model):
    """
    Define a deduction that can be assigned to employees.

    Examples:
        CIMAS
        NEC Motor Industry
        Pension
        Loan Repayment
        Salary Advance
        Funeral Cover
    """

    __tablename__ = "deduction_types"

    CATEGORY_STATUTORY = "Statutory"
    CATEGORY_VOLUNTARY = "Voluntary"
    CATEGORY_LOAN = "Loan"
    CATEGORY_GARNISHEE = "Garnishee"
    CATEGORY_OTHER = "Other"

    VALID_CATEGORIES = {
        CATEGORY_STATUTORY,
        CATEGORY_VOLUNTARY,
        CATEGORY_LOAN,
        CATEGORY_GARNISHEE,
        CATEGORY_OTHER,
    }

    CALCULATION_FIXED = "Fixed Amount"
    CALCULATION_PERCENTAGE = "Percentage"

    VALID_CALCULATION_METHODS = {
        CALCULATION_FIXED,
        CALCULATION_PERCENTAGE,
    }

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    code = db.Column(
        db.String(40),
        nullable=False,
        unique=True,
        index=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    category = db.Column(
        db.String(30),
        nullable=False,
        default=CATEGORY_VOLUNTARY,
        server_default=CATEGORY_VOLUNTARY,
    )

    calculation_method = db.Column(
        db.String(30),
        nullable=False,
        default=CALCULATION_FIXED,
        server_default=CALCULATION_FIXED,
    )

    default_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    default_percentage = db.Column(
        db.Numeric(7, 4),
        nullable=False,
        default=0,
        server_default="0",
    )

    employer_percentage = db.Column(
        db.Numeric(7, 4),
        nullable=False,
        default=0,
        server_default="0",
    )

    is_statutory = db.Column(
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

    is_tax_deductible = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    is_recurring = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
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

    employee_deductions = db.relationship(
        "EmployeeDeduction",
        back_populates="deduction_type",
        lazy="select",
        cascade="all, delete-orphan",
    )

    creator = db.relationship(
        "User",
        foreign_keys=[created_by],
    )

    __table_args__ = (
        db.CheckConstraint(
            "default_amount >= 0",
            name="ck_deduction_type_default_amount_non_negative",
        ),
        db.CheckConstraint(
            "default_percentage >= 0",
            name=(
                "ck_deduction_type_default_percentage_non_negative"
            ),
        ),
        db.CheckConstraint(
            "employer_percentage >= 0",
            name=(
                "ck_deduction_type_employer_percentage_non_negative"
            ),
        ),
    )

    def __repr__(self):
        return (
            f"<DeductionType "
            f"{self.code}: {self.name}>"
        )
