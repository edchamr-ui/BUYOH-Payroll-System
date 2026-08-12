from calendar import month_name

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    Length,
    NumberRange,
    Optional,
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


class PayrollSSPInputForm(FlaskForm):
    """Capture one employee's sickness input for a Draft period."""

    sickness_start_date = DateField(
        "Sickness Start Date",
        validators=[DataRequired()],
    )
    average_weekly_earnings = DecimalField(
        "Average Weekly Earnings",
        places=2,
        validators=[
            InputRequired(),
            NumberRange(min=0, message="Average weekly earnings cannot be negative."),
        ],
    )
    qualifying_days_per_week = IntegerField(
        "Qualifying Days per Week",
        validators=[
            InputRequired(),
            NumberRange(min=1, max=7, message="Enter between 1 and 7 qualifying days."),
        ],
    )
    qualifying_days_sick = IntegerField(
        "Qualifying Days Sick in this Period",
        validators=[
            InputRequired(),
            NumberRange(min=0, max=31, message="Enter between 0 and 31 sick days."),
        ],
    )
    salary_withheld = DecimalField(
        "Contractual Salary Withheld",
        places=2,
        default=0,
        validators=[
            InputRequired(),
            NumberRange(min=0, message="Salary withheld cannot be negative."),
        ],
    )
    notes = TextAreaField(
        "Payroll Notes",
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField("Save SSP Input")


class PayrollSMPInputForm(FlaskForm):
    """Capture one employee's maternity-pay input for a Draft period."""

    maternity_pay_period_start = DateField(
        "Maternity Pay Period Start",
        validators=[DataRequired()],
    )
    average_weekly_earnings = DecimalField(
        "Average Weekly Earnings",
        places=2,
        validators=[
            InputRequired(),
            NumberRange(min=0, message="Average weekly earnings cannot be negative."),
        ],
    )
    paid_days = IntegerField(
        "SMP Paid Days in this Period",
        validators=[
            InputRequired(),
            NumberRange(min=0, max=31, message="Enter between 0 and 31 paid days."),
        ],
    )
    salary_withheld = DecimalField(
        "Contractual Salary Withheld",
        places=2,
        default=0,
        validators=[
            InputRequired(),
            NumberRange(min=0, message="Salary withheld cannot be negative."),
        ],
    )
    eligibility_confirmed = BooleanField(
        "Employer eligibility checks completed",
        validators=[DataRequired(message="Confirm eligibility before saving SMP.")],
    )
    matb1_received = BooleanField(
        "MATB1 evidence received",
        validators=[DataRequired(message="Confirm MATB1 evidence before saving SMP.")],
    )
    notes = TextAreaField(
        "Payroll Notes",
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField("Save SMP Input")
