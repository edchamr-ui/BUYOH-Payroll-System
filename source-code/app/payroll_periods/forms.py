from calendar import month_name

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    IntegerField,
    SelectField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    NumberRange,
)


class PayrollPeriodForm(FlaskForm):
    """Form used to create and edit payroll periods."""

    month = SelectField(
        "Payroll Month",
        choices=[
            (month_number, month_name[month_number])
            for month_number in range(1, 13)
        ],
        coerce=int,
        validators=[DataRequired()],
    )

    year = IntegerField(
        "Payroll Year",
        validators=[
            DataRequired(),
            NumberRange(
                min=2020,
                max=2100,
                message="Enter a valid payroll year.",
            ),
        ],
    )

    start_date = DateField(
        "Start Date",
        validators=[DataRequired()],
    )

    end_date = DateField(
        "End Date",
        validators=[DataRequired()],
    )

    payment_date = DateField(
        "Payment Date",
        validators=[DataRequired()],
    )

    submit = SubmitField("Save Payroll Period")


class PayrollPeriodActionForm(FlaskForm):
    """CSRF-protected form for payroll workflow actions."""

    submit = SubmitField("Continue")
