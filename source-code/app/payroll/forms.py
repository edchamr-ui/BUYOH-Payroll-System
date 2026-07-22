from flask_wtf import FlaskForm
from wtforms import SubmitField


class PayrollProcessForm(FlaskForm):
    """CSRF-protected form used to process payroll."""

    submit = SubmitField("Process Payroll")
