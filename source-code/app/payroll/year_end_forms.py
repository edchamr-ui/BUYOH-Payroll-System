"""Forms for payroll year-end processing."""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
)


class PayrollYearCloseForm(FlaskForm):
    """Protected confirmation form for closing a payroll year."""

    closing_reason = TextAreaField(
        "Closing Reason",
        validators=[
            DataRequired(
                message="Enter a reason for closing the payroll year."
            ),
            Length(
                min=10,
                max=1000,
                message=(
                    "The closing reason must be between "
                    "10 and 1000 characters."
                ),
            ),
        ],
    )

    confirmation_phrase = StringField(
        "Confirmation Phrase",
        validators=[
            DataRequired(
                message="Enter the confirmation phrase."
            ),
        ],
    )

    current_password = PasswordField(
        "Current Administrator Password",
        validators=[
            DataRequired(
                message="Enter your current administrator password."
            ),
        ],
    )

    acknowledge = BooleanField(
        (
            "I understand that a closed payroll year becomes "
            "read-only and cannot be reopened through normal payroll actions."
        ),
        validators=[
            DataRequired(
                message="You must acknowledge the year-end close."
            ),
        ],
    )

    submit = SubmitField("Close Payroll Year")
