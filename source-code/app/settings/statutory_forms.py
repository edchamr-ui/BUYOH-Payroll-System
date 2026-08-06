"""Forms for statutory payroll rule management."""

from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    HiddenField,
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
    ValidationError,
)


class StatutoryRuleSetForm(FlaskForm):
    """Create or update an effective-dated statutory rule set."""

    rule_set_id = HiddenField(
        "Rule Set ID",
        validators=[
            Optional(),
        ],
    )

    name = StringField(
        "Rule Set Name",
        validators=[
            DataRequired(
                message="Rule set name is required."
            ),
            Length(
                min=3,
                max=150,
                message=(
                    "Rule set name must contain between "
                    "3 and 150 characters."
                ),
            ),
        ],
    )

    currency = SelectField(
        "Currency",
        choices=[
            (
                "USD",
                "USD — United States Dollar",
            ),
            (
                "ZWG",
                "ZWG — Zimbabwe Gold",
            ),
            (
                "ZAR",
                "ZAR — South African Rand",
            ),
        ],
        validators=[
            DataRequired(
                message="Currency is required."
            ),
        ],
    )

    effective_from = DateField(
        "Effective From",
        format="%Y-%m-%d",
        validators=[
            DataRequired(
                message=(
                    "Effective-from date is required."
                )
            ),
        ],
    )

    effective_to = DateField(
        "Effective To",
        format="%Y-%m-%d",
        validators=[
            Optional(),
        ],
    )

    nssa_employee_percentage = DecimalField(
        "NSSA Employee Rate (%)",
        places=4,
        default=0,
        validators=[
            DataRequired(
                message=(
                    "Employee NSSA rate is required."
                )
            ),
            NumberRange(
                min=0,
                max=100,
                message=(
                    "Employee NSSA rate must be "
                    "between 0 and 100."
                ),
            ),
        ],
    )

    nssa_employer_percentage = DecimalField(
        "NSSA Employer Rate (%)",
        places=4,
        default=0,
        validators=[
            DataRequired(
                message=(
                    "Employer NSSA rate is required."
                )
            ),
            NumberRange(
                min=0,
                max=100,
                message=(
                    "Employer NSSA rate must be "
                    "between 0 and 100."
                ),
            ),
        ],
    )

    nssa_monthly_ceiling = DecimalField(
        "NSSA Monthly Insurable Earnings Ceiling",
        places=2,
        default=0,
        validators=[
            DataRequired(
                message=(
                    "NSSA monthly ceiling is required."
                )
            ),
            NumberRange(
                min=0,
                message=(
                    "NSSA monthly ceiling cannot "
                    "be negative."
                ),
            ),
        ],
    )

    aids_levy_percentage = DecimalField(
        "AIDS Levy Rate (%)",
        places=4,
        default=0,
        validators=[
            DataRequired(
                message=(
                    "AIDS Levy rate is required."
                )
            ),
            NumberRange(
                min=0,
                max=100,
                message=(
                    "AIDS Levy rate must be between "
                    "0 and 100."
                ),
            ),
        ],
    )

    paye_enabled = BooleanField(
        "Enable PAYE calculations",
        default=False,
    )

    is_active = BooleanField(
        "Active rule set",
        default=True,
    )

    submit = SubmitField(
        "Save Statutory Rule Set",
    )

    def validate_effective_to(
        self,
        field,
    ):
        """Ensure the ending date is not before the starting date."""

        if (
            field.data is not None
            and self.effective_from.data is not None
            and field.data < self.effective_from.data
        ):
            raise ValidationError(
                (
                    "Effective-to date cannot be earlier "
                    "than the effective-from date."
                )
            )


class StatutoryActionForm(FlaskForm):
    """Provide CSRF protection for statutory-rule actions."""

    submit = SubmitField(
        "Submit",
    )


class StatutoryPresetImportForm(FlaskForm):
    """Import one verified statutory preset."""

    preset_key = SelectField(
        "Verified Statutory Preset",
        choices=[],
        validators=[
            DataRequired(
                message=(
                    "Select a statutory preset to import."
                )
            ),
        ],
    )

    activate = BooleanField(
        "Activate this rule set after import",
        default=True,
    )

    confirm_verified_source = BooleanField(
        (
            "I understand that only the displayed verified "
            "tax year and currency will be imported."
        ),
        validators=[
            DataRequired(
                message=(
                    "Confirm that you reviewed the preset "
                    "tax year, currency and source."
                )
            ),
        ],
    )

    submit = SubmitField(
        "Import Statutory Preset",
    )


class TaxBandForm(FlaskForm):
    """Create or edit one progressive PAYE tax band."""

    tax_band_id = HiddenField(
        "Tax Band ID",
        validators=[
            Optional(),
        ],
    )

    band_order = IntegerField(
        "Band Order",
        validators=[
            DataRequired(
                message="Band order is required."
            ),
            NumberRange(
                min=1,
                max=100,
                message=(
                    "Band order must be between "
                    "1 and 100."
                ),
            ),
        ],
    )

    lower_limit = DecimalField(
        "Lower Limit",
        places=2,
        validators=[
            DataRequired(
                message="Lower limit is required."
            ),
            NumberRange(
                min=0,
                message=(
                    "Lower limit cannot be negative."
                ),
            ),
        ],
    )

    upper_limit = DecimalField(
        "Upper Limit",
        places=2,
        validators=[
            Optional(),
            NumberRange(
                min=0,
                message=(
                    "Upper limit cannot be negative."
                ),
            ),
        ],
    )

    rate_percentage = DecimalField(
        "Tax Rate (%)",
        places=4,
        validators=[
            DataRequired(
                message="Tax rate is required."
            ),
            NumberRange(
                min=0,
                max=100,
                message=(
                    "Tax rate must be between "
                    "0 and 100."
                ),
            ),
        ],
    )

    submit = SubmitField(
        "Save Tax Band",
    )

    def validate_upper_limit(
        self,
        field,
    ):
        """Ensure the upper limit exceeds the lower limit."""

        if (
            field.data is not None
            and self.lower_limit.data is not None
            and field.data <= self.lower_limit.data
        ):
            raise ValidationError(
                (
                    "Upper limit must be greater "
                    "than the lower limit."
                )
            )

    def validate_rate_percentage(
        self,
        field,
    ):
        """Reject invalid negative or excessive tax rates."""

        if field.data is None:
            return

        rate = Decimal(
            str(field.data)
        )

        if rate < Decimal("0"):
            raise ValidationError(
                "Tax rate cannot be negative."
            )

        if rate > Decimal("100"):
            raise ValidationError(
                "Tax rate cannot exceed 100%."
            )


class TaxBandActionForm(FlaskForm):
    """Provide CSRF protection for tax-band actions."""

    submit = SubmitField(
        "Submit",
    )


class PAYECalculationTestForm(FlaskForm):
    """Test a statutory rule set against a sample monthly salary."""

    gross_salary = DecimalField(
        "Gross Monthly Salary",
        places=2,
        validators=[
            DataRequired(
                message=(
                    "Enter a gross monthly salary."
                )
            ),
            NumberRange(
                min=0,
                message=(
                    "Gross salary cannot be negative."
                ),
            ),
        ],
    )

    calculate = SubmitField(
        "Calculate Payroll Preview",
    )
