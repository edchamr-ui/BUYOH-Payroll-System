"""Forms for administrator-only payroll reset operations."""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    ValidationError,
)


class BasePayrollResetForm(FlaskForm):
    """Base confirmation form shared by all payroll reset levels."""

    confirmation_phrase = StringField(
        "Confirmation Phrase",
        validators=[
            DataRequired(
                message=(
                    "Enter the required confirmation phrase."
                )
            ),
        ],
    )

    current_password = PasswordField(
        "Current Administrator Password",
        validators=[
            DataRequired(
                message=(
                    "Enter your current administrator password."
                )
            ),
        ],
    )

    acknowledge = BooleanField(
        (
            "I understand that this operation is permanent "
            "and cannot be undone."
        ),
        validators=[
            DataRequired(
                message=(
                    "You must acknowledge that this operation "
                    "cannot be undone."
                )
            ),
        ],
    )

    expected_phrase = ""

    def validate_confirmation_phrase(
        self,
        field,
    ):
        """Require the exact confirmation phrase."""

        submitted_phrase = str(
            field.data or ""
        ).strip()

        if submitted_phrase != self.expected_phrase:
            raise ValidationError(
                (
                    f'Type "{self.expected_phrase}" '
                    "exactly to continue."
                )
            )


class PayrollHistoryResetForm(
    BasePayrollResetForm
):
    """Confirm deletion of payroll history."""

    expected_phrase = (
        "DELETE PAYROLL HISTORY"
    )

    submit = SubmitField(
        "Permanently Delete Payroll History",
    )


class PayrollConfigurationResetForm(
    BasePayrollResetForm
):
    """Confirm deletion of recurring payroll configuration."""

    expected_phrase = (
        "DELETE PAYROLL CONFIGURATION"
    )

    submit = SubmitField(
        "Permanently Delete Payroll Configuration",
    )


class PayrollFactoryResetForm(
    BasePayrollResetForm
):
    """Confirm a payroll-domain factory reset."""

    expected_phrase = (
        "FACTORY RESET PAYROLL"
    )

    submit = SubmitField(
        "Permanently Reset Payroll",
    )
