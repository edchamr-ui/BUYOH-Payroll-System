from datetime import date, datetime
from decimal import Decimal

from app.extensions import db


class StatutoryRuleSet(db.Model):
    """
    Store effective-dated operational statutory payroll configuration.

    Library-import provenance is retained so installed packages can
    be distinguished from manually created rule sets and compared
    with newer library versions.
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

    source_preset_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "statutory_presets.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    source_preset_key = db.Column(
        db.String(120),
        nullable=True,
        index=True,
    )

    source_preset_version = db.Column(
        db.String(50),
        nullable=True,
    )

    source_engine_type = db.Column(
        db.String(80),
        nullable=True,
        index=True,
    )

    source_country_code = db.Column(
        db.String(2),
        nullable=True,
        index=True,
    )

    imported_from_library = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    imported_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    imported_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
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

    source_preset = db.relationship(
        "StatutoryPreset",
        foreign_keys=[source_preset_id],
        lazy="select",
    )

    imported_by_user = db.relationship(
        "User",
        foreign_keys=[imported_by_user_id],
        lazy="select",
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
        return (
            f"{self.name} - {self.currency} "
            f"({self.effective_from:%d %b %Y})"
        )

    @property
    def installed_version_label(self):
        return (
            self.source_preset_version
            if self.imported_from_library
            else None
        )

    @property
    def has_library_update(self):
        if (
            not self.imported_from_library
            or self.source_preset is None
            or not self.source_preset_version
        ):
            return False

        return (
            str(self.source_preset.version)
            != str(self.source_preset_version)
        )

    def applies_on(self, calculation_date):
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
            f"currency={self.currency!r} "
            f"source_preset_key={self.source_preset_key!r}>"
        )
