"""Statutory preset contribution model."""

from datetime import datetime

from app.extensions import db
from app.time_utils import legacy_utc_now


class StatutoryPresetContribution(db.Model):
    """
    Store one statutory contribution attached to a library preset.

    Examples:
        Zimbabwe:
            NSSA

        Zambia:
            NAPSA

        South Africa:
            UIF
            SDL

        Kenya:
            NSSF
            SHIF
            Affordable Housing Levy

        United Kingdom:
            National Insurance

        Canada:
            CPP
            EI

        United States:
            Social Security
            Medicare
    """

    __tablename__ = "statutory_preset_contributions"

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

    code = db.Column(
        db.String(80),
        nullable=False,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    employee_rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=0,
    )

    employer_rate = db.Column(
        db.Numeric(8, 6),
        nullable=False,
        default=0,
    )

    employee_fixed_amount = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=0,
    )

    employer_fixed_amount = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=0,
    )

    lower_threshold = db.Column(
        db.Numeric(14, 2),
        nullable=False,
        default=0,
    )

    earnings_ceiling = db.Column(
        db.Numeric(14, 2),
        nullable=True,
    )

    calculation_basis = db.Column(
        db.String(30),
        nullable=False,
        default="GROSS",
    )

    calculation_method = db.Column(
        db.String(30),
        nullable=False,
        default="RATE",
    )

    reduces_taxable_income = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    included_in_employer_cost = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    is_employee_contribution = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    is_employer_contribution = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    display_order = db.Column(
        db.Integer,
        nullable=False,
        default=1,
    )

    notes = db.Column(
        db.Text,
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

    preset = db.relationship(
        "StatutoryPreset",
        back_populates="contributions",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "preset_id",
            "code",
            name=(
                "uq_statutory_preset_contribution_"
                "preset_code"
            ),
        ),

        db.CheckConstraint(
            "employee_rate >= 0 "
            "AND employee_rate <= 1",
            name=(
                "ck_statutory_preset_contribution_"
                "employee_rate"
            ),
        ),

        db.CheckConstraint(
            "employer_rate >= 0 "
            "AND employer_rate <= 1",
            name=(
                "ck_statutory_preset_contribution_"
                "employer_rate"
            ),
        ),

        db.CheckConstraint(
            "employee_fixed_amount >= 0",
            name=(
                "ck_statutory_preset_contribution_"
                "employee_fixed"
            ),
        ),

        db.CheckConstraint(
            "employer_fixed_amount >= 0",
            name=(
                "ck_statutory_preset_contribution_"
                "employer_fixed"
            ),
        ),

        db.CheckConstraint(
            "lower_threshold >= 0",
            name=(
                "ck_statutory_preset_contribution_"
                "threshold"
            ),
        ),

        db.CheckConstraint(
            (
                "earnings_ceiling IS NULL "
                "OR earnings_ceiling >= 0"
            ),
            name=(
                "ck_statutory_preset_contribution_"
                "ceiling"
            ),
        ),

        db.CheckConstraint(
            (
                "earnings_ceiling IS NULL "
                "OR earnings_ceiling >= lower_threshold"
            ),
            name=(
                "ck_statutory_preset_contribution_"
                "ceiling_threshold"
            ),
        ),

        db.CheckConstraint(
            (
                "calculation_basis IN "
                "('GROSS', 'TAXABLE', 'PENSIONABLE')"
            ),
            name=(
                "ck_statutory_preset_contribution_"
                "basis"
            ),
        ),

        db.CheckConstraint(
            (
                "calculation_method IN "
                "('RATE', 'FIXED', 'RATE_PLUS_FIXED')"
            ),
            name=(
                "ck_statutory_preset_contribution_"
                "method"
            ),
        ),

        db.CheckConstraint(
            "display_order >= 1",
            name=(
                "ck_statutory_preset_contribution_"
                "display_order"
            ),
        ),
    )

    @property
    def employee_rate_percentage(self):
        """Return employee rate expressed as a percentage."""

        return (
            float(self.employee_rate or 0)
            * 100
        )

    @property
    def employer_rate_percentage(self):
        """Return employer rate expressed as a percentage."""

        return (
            float(self.employer_rate or 0)
            * 100
        )

    @property
    def has_ceiling(self):
        """Return whether this contribution has an earnings ceiling."""

        return (
            self.earnings_ceiling is not None
        )

    def __repr__(self):
        return (
            "<StatutoryPresetContribution "
            f"preset_id={self.preset_id} "
            f"code={self.code!r} "
            f"name={self.name!r}>"
        )
