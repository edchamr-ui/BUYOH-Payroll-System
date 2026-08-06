"""Database-backed statutory library preset model."""

from datetime import date, datetime

from app.extensions import db


class StatutoryPreset(db.Model):
    """Store one versioned statutory library preset."""

    __tablename__ = "statutory_presets"

    ENGINE_ZIMBABWE = "ZIMBABWE_PROGRESSIVE"
    ENGINE_ZAMBIA = "ZAMBIA_PROGRESSIVE"
    ENGINE_BOTSWANA = "BOTSWANA_PAYE"
    ENGINE_NAMIBIA = "NAMIBIA_ANNUAL"
    ENGINE_SOUTH_AFRICA = "SOUTH_AFRICA_REBATE"
    ENGINE_KENYA = "KENYA_RELIEF"

    SUPPORTED_ENGINE_TYPES = (
        ENGINE_ZIMBABWE,
        ENGINE_ZAMBIA,
        ENGINE_BOTSWANA,
        ENGINE_NAMIBIA,
        ENGINE_SOUTH_AFRICA,
        ENGINE_KENYA,
    )

    id = db.Column(db.Integer, primary_key=True)

    preset_key = db.Column(
        db.String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    country_code = db.Column(
        db.String(2),
        nullable=False,
        index=True,
    )

    country_name = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    country_flag = db.Column(
        db.String(16),
        nullable=True,
    )

    currency = db.Column(
        db.String(3),
        nullable=False,
        index=True,
    )

    tax_year = db.Column(
        db.Integer,
        nullable=False,
        index=True,
    )

    tax_period_label = db.Column(
        db.String(100),
        nullable=True,
    )

    version = db.Column(
        db.String(50),
        nullable=False,
        default="1.0",
    )

    name = db.Column(
        db.String(180),
        nullable=False,
    )

    engine_type = db.Column(
        db.String(80),
        nullable=False,
        default=ENGINE_ZIMBABWE,
        index=True,
    )

    effective_from = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    effective_to = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    verification_status = db.Column(
        db.String(30),
        nullable=False,
        default="Draft",
        index=True,
    )

    source_name = db.Column(
        db.String(255),
        nullable=False,
    )

    source_description = db.Column(
        db.Text,
        nullable=True,
    )

    source_reference = db.Column(
        db.String(500),
        nullable=True,
    )

    official_source_url = db.Column(
        db.String(1000),
        nullable=True,
    )

    last_verified_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    paye_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    employee_contribution_name = db.Column(
        db.String(100),
        nullable=True,
    )

    employee_contribution_rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=0,
    )

    employer_contribution_name = db.Column(
        db.String(100),
        nullable=True,
    )

    employer_contribution_rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=0,
    )

    contribution_ceiling = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=0,
    )

    levy_name = db.Column(
        db.String(100),
        nullable=True,
    )

    levy_rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=0,
    )

    supports_import = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    supports_payroll = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    is_published = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    is_locked = db.Column(
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

    bands = db.relationship(
        "StatutoryPresetBand",
        back_populates="preset",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="StatutoryPresetBand.band_order",
    )

    __table_args__ = (
        db.CheckConstraint(
            "tax_year >= 1900",
            name="ck_statutory_preset_tax_year",
        ),
        db.CheckConstraint(
            "effective_to >= effective_from",
            name="ck_statutory_preset_effective_dates",
        ),
        db.CheckConstraint(
            "employee_contribution_rate >= 0 "
            "AND employee_contribution_rate <= 1",
            name="ck_statutory_preset_employee_rate",
        ),
        db.CheckConstraint(
            "employer_contribution_rate >= 0 "
            "AND employer_contribution_rate <= 1",
            name="ck_statutory_preset_employer_rate",
        ),
        db.CheckConstraint(
            "levy_rate >= 0 AND levy_rate <= 1",
            name="ck_statutory_preset_levy_rate",
        ),
        db.CheckConstraint(
            "contribution_ceiling >= 0",
            name="ck_statutory_preset_ceiling",
        ),
        db.UniqueConstraint(
            "country_code",
            "currency",
            "tax_year",
            "effective_from",
            "version",
            name="uq_statutory_preset_country_currency_year",
        ),
    )

    @property
    def display_name(self):
        """Return the human-readable library label."""

        period = (
            self.tax_period_label
            or str(self.tax_year)
        )

        return (
            f"{self.country_name} "
            f"{self.currency} "
            f"{period}"
        )

    @property
    def is_verified(self):
        """Return whether the preset is explicitly verified."""

        return (
            str(self.verification_status or "")
            .strip()
            .lower()
            == "verified"
        )

    @property
    def import_status(self):
        """Return the preset's current library and import status."""

        verification = (
            str(self.verification_status or "")
            .strip()
            .lower()
        )

        if (
            self.supports_import
            and self.supports_payroll
            and self.is_verified
        ):
            return "Ready to Import"

        if (
            self.is_verified
            and not self.supports_payroll
        ):
            return "Engine Upgrade Required"

        if verification == "source located":
            return "Verification Required"

        if verification == "draft":
            return "Draft"

        return "Not Ready"


    @property
    def can_import(self):
        """Return whether this preset may be imported."""

        return bool(
            self.is_published
            and self.is_verified
            and self.supports_import
            and self.supports_payroll
        )

    def applies_on(self, calculation_date):
        """Return whether the preset covers the supplied date."""

        if not isinstance(calculation_date, date):
            raise TypeError(
                "Calculation date must be a date object."
            )

        return (
            self.effective_from
            <= calculation_date
            <= self.effective_to
        )

    def __repr__(self):
        return (
            f"<StatutoryPreset "
            f"key={self.preset_key!r} "
            f"country={self.country_code!r} "
            f"currency={self.currency!r} "
            f"year={self.tax_year} "
            f"engine={self.engine_type!r}>"
        )
