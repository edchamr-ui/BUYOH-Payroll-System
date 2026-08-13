"""Reusable allowance-type definitions."""

from datetime import datetime

from app.extensions import db
from app.time_utils import legacy_utc_now


class AllowanceType(db.Model):
    """
    Define an allowance that can be assigned to employees.

    Examples:
        Housing Allowance
        Transport Allowance
        Meal Allowance
        Shift Allowance
        Commission
    """

    __tablename__ = "allowance_types"

    CALCULATION_FIXED = "Fixed Amount"
    CALCULATION_PERCENTAGE = "Percentage"

    VALID_CALCULATION_METHODS = {
        CALCULATION_FIXED,
        CALCULATION_PERCENTAGE,
    }

    EARNING_REGULAR = "Regular Allowance"
    EARNING_BONUS = "Bonus"
    EARNING_COMMISSION = "Commission"
    EARNING_TAXABLE_BENEFIT = "Taxable Benefit"

    VALID_EARNING_CLASSIFICATIONS = {
        EARNING_REGULAR,
        EARNING_BONUS,
        EARNING_COMMISSION,
        EARNING_TAXABLE_BENEFIT,
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

    is_taxable = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    earning_classification = db.Column(
        db.String(30),
        nullable=False,
        default=EARNING_REGULAR,
        server_default=EARNING_REGULAR,
        index=True,
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
        default=legacy_utc_now,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=legacy_utc_now,
        onupdate=legacy_utc_now,
    )

    employee_allowances = db.relationship(
        "EmployeeAllowance",
        back_populates="allowance_type",
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
            name="ck_allowance_type_default_amount_non_negative",
        ),
        db.CheckConstraint(
            "default_percentage >= 0",
            name=(
                "ck_allowance_type_default_percentage_non_negative"
            ),
        ),
    )

    def __repr__(self):
        return (
            f"<AllowanceType "
            f"{self.code}: {self.name}>"
        )
