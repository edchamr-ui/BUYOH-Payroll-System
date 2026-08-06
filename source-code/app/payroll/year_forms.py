"""Forms for payroll year management inside the payroll module."""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    NumberRange,
    ValidationError,
)


class PayrollYearCreateForm(FlaskForm):
    """Create a payroll year and all twelve monthly periods."""

    year = IntegerField(
        "Payroll Year",
        default=date.today().year,
        validators=[
            DataRequired(),
            NumberRange(
                min=2020,
                max=2100,
                message=(
                    "Enter a year between 2020 and 2100."
                ),
            ),
        ],
    )

    payment_day = IntegerField(
        "Default Payment Day",
        default=25,
        validators=[
            DataRequired(),
            NumberRange(
                min=1,
                max=31,
                message=(
                    "Enter a payment day between 1 and 31."
                ),
            ),
        ],
    )

    clamp_payment_day = BooleanField(
        (
            "Use the month's final day when the "
            "selected day does not exist"
        ),
        default=True,
    )

    submit = SubmitField(
        "Create Payroll Year"
    )

    def validate_year(
        self,
        field,
    ):
        """Prevent accidentally creating very old payroll years."""

        if field.data < date.today().year - 5:
            raise ValidationError(
                (
                    "Creating a payroll year more than "
                    "five years in the past is not permitted."
                )
            )
