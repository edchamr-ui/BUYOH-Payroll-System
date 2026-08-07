"""Forms for the Statutory Package Builder."""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)


class StatutoryPackageStepOneForm(FlaskForm):
    """Capture the statutory package identity and effective period."""

    country_code = StringField(
        "Country Code",
        validators=[
            DataRequired(),
            Length(min=2, max=2),
            Regexp(
                r"^[A-Za-z]{2}$",
                message=(
                    "Use a two-letter country code, "
                    "for example BW, ZW or GB."
                ),
            ),
        ],
    )

    country_name = StringField(
        "Country Name",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
    )

    country_flag = StringField(
        "Country Flag",
        validators=[
            Optional(),
            Length(max=10),
        ],
        description="Optional emoji flag, for example 🇧🇼.",
    )

    currency = StringField(
        "Currency",
        validators=[
            DataRequired(),
            Length(min=3, max=3),
            Regexp(
                r"^[A-Za-z]{3}$",
                message=(
                    "Use a three-letter currency code, "
                    "for example BWP, USD or GBP."
                ),
            ),
        ],
    )

    tax_year = IntegerField(
        "Tax Year",
        validators=[
            DataRequired(),
            NumberRange(min=2020, max=2100),
        ],
        default=lambda: date.today().year,
    )

    tax_period_label = SelectField(
        "Tax Period",
        choices=[
            ("Monthly", "Monthly"),
            ("Annual", "Annual"),
            ("Weekly", "Weekly"),
            ("Biweekly", "Biweekly"),
        ],
        validators=[
            DataRequired(),
        ],
        default="Monthly",
    )

    package_name = StringField(
        "Package Name",
        validators=[
            DataRequired(),
            Length(max=200),
        ],
        description=(
            "Example: Botswana BWP PAYE Rules 2026."
        ),
    )

    preset_key = StringField(
        "Preset Key",
        validators=[
            DataRequired(),
            Length(max=120),
            Regexp(
                r"^[A-Za-z0-9_]+$",
                message=(
                    "Use only letters, numbers and underscores."
                ),
            ),
        ],
        description=(
            "Example: BW_BWP_2026_MONTHLY."
        ),
    )

    engine_type = StringField(
        "Calculation Engine",
        validators=[
            DataRequired(),
            Length(max=100),
            Regexp(
                r"^[A-Za-z0-9_]+$",
                message=(
                    "Use only letters, numbers and underscores."
                ),
            ),
        ],
        description=(
            "Example: BOTSWANA_PAYE."
        ),
    )

    version = StringField(
        "Package Version",
        validators=[
            DataRequired(),
            Length(max=30),
        ],
        default="1.0",
    )

    effective_from = DateField(
        "Effective From",
        validators=[
            DataRequired(),
        ],
        format="%Y-%m-%d",
    )

    effective_to = DateField(
        "Effective To",
        validators=[
            Optional(),
        ],
        format="%Y-%m-%d",
    )

    paye_enabled = BooleanField(
        "This package includes PAYE",
        default=True,
    )

    submit = SubmitField(
        "Save Draft and Continue",
    )

    def validate_effective_to(
        self,
        field,
    ):
        """Ensure the end date follows the start date."""

        if (
            field.data is not None
            and self.effective_from.data is not None
            and field.data < self.effective_from.data
        ):
            raise ValidationError(
                "The effective end date cannot be before "
                "the effective start date."
            )
