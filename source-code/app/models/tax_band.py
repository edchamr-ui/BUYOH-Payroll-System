from decimal import Decimal

from app.extensions import db


class TaxBand(db.Model):
    """
    Stores one progressive PAYE tax band.

    An upper limit of NULL means the band has no maximum.
    """

    __tablename__ = "tax_bands"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    rule_set_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "statutory_rule_sets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    band_order = db.Column(
        db.Integer,
        nullable=False,
    )

    lower_limit = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    upper_limit = db.Column(
        db.Numeric(14, 2),
        nullable=True,
    )

    rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=Decimal("0.000000"),
    )

    rule_set = db.relationship(
        "StatutoryRuleSet",
        back_populates="tax_bands",
    )

    __table_args__ = (
        db.CheckConstraint(
            "band_order > 0",
            name="ck_tax_band_order_positive",
        ),
        db.CheckConstraint(
            "lower_limit >= 0",
            name="ck_tax_band_lower_limit_non_negative",
        ),
        db.CheckConstraint(
            "upper_limit IS NULL "
            "OR upper_limit > lower_limit",
            name="ck_tax_band_valid_range",
        ),
        db.CheckConstraint(
            "rate >= 0 AND rate <= 1",
            name="ck_tax_band_rate",
        ),
        db.UniqueConstraint(
            "rule_set_id",
            "band_order",
            name="uq_tax_band_rule_set_order",
        ),
    )

    @property
    def rate_percentage(self):
        """Return the tax rate as a percentage."""

        return Decimal(str(self.rate)) * Decimal("100")

    def __repr__(self):
        return (
            f"<TaxBand "
            f"order={self.band_order} "
            f"lower={self.lower_limit} "
            f"upper={self.upper_limit} "
            f"rate={self.rate}>"
        )
