"""Progressive PAYE band belonging to a statutory preset."""

from decimal import Decimal

from app.extensions import db


class StatutoryPresetBand(db.Model):
    """Stores one progressive tax band in the statutory library."""

    __tablename__ = "statutory_preset_bands"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    preset_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "statutory_presets.id",
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

    preset = db.relationship(
        "StatutoryPreset",
        back_populates="bands",
    )

    __table_args__ = (
        db.CheckConstraint(
            "band_order > 0",
            name="ck_statutory_preset_band_order",
        ),
        db.CheckConstraint(
            "lower_limit >= 0",
            name="ck_statutory_preset_band_lower",
        ),
        db.CheckConstraint(
            "upper_limit IS NULL "
            "OR upper_limit > lower_limit",
            name="ck_statutory_preset_band_range",
        ),
        db.CheckConstraint(
            "rate >= 0 AND rate <= 1",
            name="ck_statutory_preset_band_rate",
        ),
        db.UniqueConstraint(
            "preset_id",
            "band_order",
            name="uq_statutory_preset_band_order",
        ),
    )

    @property
    def rate_percentage(self):
        """Return the decimal rate as a percentage."""

        return (
            Decimal(str(self.rate))
            * Decimal("100")
        )

    def __repr__(self):
        return (
            f"<StatutoryPresetBand "
            f"preset_id={self.preset_id} "
            f"order={self.band_order} "
            f"rate={self.rate}>"
        )
