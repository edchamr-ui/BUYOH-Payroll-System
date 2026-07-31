"""Forms for email delivery actions."""

from flask_wtf import FlaskForm
from wtforms import SubmitField


class ResendEmailForm(FlaskForm):
    """Validate a request to resend a payslip email."""

    submit = SubmitField("Resend")

