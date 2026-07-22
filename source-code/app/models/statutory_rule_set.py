from datetime import date, datetime
from decimal import Decimal

from app.extensions import db


class StatutoryRuleSet(db.Model):
    """
    Stores effective-dated statutory payroll configuration.

    A rule set represents the statutory rates applicable to one
    currency during a defined period.
    """

    __tablename__ = "statutory_rule_sets"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
    )

    currency = db.Column(
        db.String(3),
        nullable=False,
        index=True,
    )

    effective_from = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    effective_to = db.Column(
        db.Date,
        nullable=True,
        index=True,
    )

    nssa_employee_rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=Decimal("0.000000"),
    )

    nssa_employer_rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=Decimal("0.000000"),
    )

    nssa_monthly_ceiling = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    aids_levy_rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=Decimal("0.000000"),
    )

    paye_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
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

    tax_bands = db.relationship(
        "TaxBand",
        back_populates="rule_set",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="TaxBand.band_order",
    )

    __table_args__ = (
        db.CheckConstraint(
            "nssa_employee_rate >= 0 "
            "AND nssa_employee_rate <= 1",
            name="ck_rule_set_nssa_employee_rate",
        ),
        db.CheckConstraint(
            "nssa_employer_rate >= 0 "
            "AND nssa_employer_rate <= 1",
            name="ck_rule_set_nssa_employer_rate",
        ),
        db.CheckConstraint(
            "aids_levy_rate >= 0 "
            "AND aids_levy_rate <= 1",
            name="ck_rule_set_aids_levy_rate",
        ),
        db.CheckConstraint(
            "nssa_monthly_ceiling >= 0",
            name="ck_rule_set_nssa_ceiling_non_negative",
        ),
        db.CheckConstraint(
            "effective_to IS NULL "
            "OR effective_to >= effective_from",
            name="ck_rule_set_effective_date_range",
        ),
        db.UniqueConstraint(
            "name",
            "currency",
            "effective_from",
            name="uq_rule_set_name_currency_effective_from",
        ),
    )

    @property
    def display_name(self):
        """Return a readable rule-set label."""

        return (
            f"{self.name} - {self.currency} "
            f"({self.effective_from:%d %b %Y})"
        )

    def applies_on(self, calculation_date):
        """Return True when this rule set applies on a date."""

        if not isinstance(calculation_date, date):
            raise TypeError(
                "Calculation date must be a date object."
            )

        if calculation_date < self.effective_from:
            return False

        if (
            self.effective_to is not None
            and calculation_date > self.effective_to
        ):
            return False

        return self.is_active

    def __repr__(self):
        return (
            f"<StatutoryRuleSet "
            f"name={self.name!r} "
            f"currency={self.currency!r}>"
        )
