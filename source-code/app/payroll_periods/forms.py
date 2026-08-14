from calendar import month_name
from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    SubmitField,
    TextAreaField,
    StringField,
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


class PayrollOvertimeInputForm(FlaskForm):
    """Capture a period-specific overtime calculation snapshot."""

    category = SelectField(
        "Overtime Category",
        choices=(
            ("Ordinary", "Ordinary overtime"),
            ("Saturday", "Saturday"),
            ("Sunday", "Sunday"),
            ("Public Holiday", "Public holiday"),
            ("Night", "Night overtime"),
            ("Other", "Other"),
        ),
        validators=[DataRequired()],
    )
    work_date = DateField("Work Date", validators=[Optional()])
    hours = DecimalField(
        "Hours Worked",
        places=2,
        validators=[
            InputRequired(),
            NumberRange(
                min=Decimal("0.01"),
                max=Decimal("744"),
                message="Enter overtime hours between 0.01 and 744.",
            ),
        ],
    )
    hourly_rate = DecimalField(
        "Hourly Rate",
        places=4,
        validators=[
            InputRequired(),
            NumberRange(min=0, message="Hourly rate cannot be negative."),
        ],
    )
    multiplier = DecimalField(
        "Multiplier",
        places=4,
        default=Decimal("1.5"),
        validators=[
            InputRequired(),
            NumberRange(
                min=Decimal("0.0001"),
                max=Decimal("10"),
                message="Enter a multiplier greater than zero and not above 10.",
            ),
        ],
    )
    description = TextAreaField(
        "Description or Approval Reference",
        validators=[Optional(), Length(max=300)],
    )
    submit = SubmitField("Save Overtime Input")


class PayrollOneOffDeductionForm(FlaskForm):
    """Capture a period-specific net-pay deduction."""

    deduction_type = SelectField(
        "Deduction Type",
        choices=(
            ("Salary Advance Recovery", "Salary advance recovery"),
            ("Employee Loan Repayment", "Employee loan repayment"),
            ("Staff Purchase", "Staff purchase"),
            ("Uniform or Equipment Recovery", "Uniform or equipment recovery"),
            ("Medical Recovery", "Medical recovery"),
            ("Other One-Off Deduction", "Other one-off deduction"),
        ),
        validators=[DataRequired()],
    )
    amount = DecimalField(
        "Deduction Amount",
        places=2,
        validators=[
            InputRequired(),
            NumberRange(
                min=Decimal("0.01"),
                message="The deduction must be greater than zero.",
            ),
        ],
    )
    priority = IntegerField(
        "Recovery Priority",
        default=100,
        validators=[
            InputRequired(),
            NumberRange(
                min=0,
                max=999,
                message="Enter a priority between 0 and 999.",
            ),
        ],
    )
    description = TextAreaField(
        "Description or Approval Reference",
        validators=[Optional(), Length(max=300)],
    )
    submit = SubmitField("Save One-Off Deduction")


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


class PayrollSPPInputForm(FlaskForm):
    """Capture one employee's paternity-pay input for a Draft period."""

    paternity_pay_period_start = DateField(
        "Paternity Pay Period Start",
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
        "SPP Paid Days in this Period",
        validators=[
            InputRequired(),
            NumberRange(min=0, max=14, message="Enter between 0 and 14 paid days."),
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
        validators=[DataRequired(message="Confirm eligibility before saving SPP.")],
    )
    declaration_received = BooleanField(
        "Employee declaration or evidence received",
        validators=[DataRequired(message="Confirm the declaration before saving SPP.")],
    )
    notes = TextAreaField(
        "Payroll Notes",
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField("Save SPP Input")


class PayrollSAPInputForm(FlaskForm):
    """Capture one employee's adoption-pay input for a Draft period."""
    adoption_pay_period_start = DateField("Adoption Pay Period Start", validators=[DataRequired()])
    average_weekly_earnings = DecimalField("Average Weekly Earnings", places=2, validators=[InputRequired(), NumberRange(min=0, message="Average weekly earnings cannot be negative.")])
    paid_days = IntegerField("SAP Paid Days in this Period", validators=[InputRequired(), NumberRange(min=0, max=31, message="Enter between 0 and 31 paid days.")])
    salary_withheld = DecimalField("Contractual Salary Withheld", places=2, default=0, validators=[InputRequired(), NumberRange(min=0, message="Salary withheld cannot be negative.")])
    eligibility_confirmed = BooleanField("Employer eligibility checks completed", validators=[DataRequired(message="Confirm eligibility before saving SAP.")])
    adoption_evidence_received = BooleanField("Adoption evidence received", validators=[DataRequired(message="Confirm adoption evidence before saving SAP.")])
    notes = TextAreaField("Payroll Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save SAP Input")


class PayrollShPPInputForm(FlaskForm):
    entitlement_reference = StringField("Entitlement Reference", validators=[DataRequired(), Length(max=80)])
    shared_pay_period_start = DateField("Shared Pay Period Start", validators=[DataRequired()])
    average_weekly_earnings = DecimalField("Average Weekly Earnings", places=2, validators=[InputRequired(), NumberRange(min=0, message="Average weekly earnings cannot be negative.")])
    allocated_days = IntegerField("Transferred Pay Allocation (Days)", validators=[InputRequired(), NumberRange(min=0, max=259, message="Enter between 0 and 259 allocated days.")])
    paid_days = IntegerField("ShPP Paid Days in this Period", validators=[InputRequired(), NumberRange(min=0, max=31, message="Enter between 0 and 31 paid days.")])
    salary_withheld = DecimalField("Contractual Salary Withheld", places=2, default=0, validators=[InputRequired(), NumberRange(min=0, message="Salary withheld cannot be negative.")])
    eligibility_confirmed = BooleanField("Employer eligibility checks completed", validators=[DataRequired(message="Confirm eligibility before saving ShPP.")])
    curtailment_notice_received = BooleanField("Curtailment notice received", validators=[DataRequired(message="Confirm the curtailment notice before saving ShPP.")])
    partner_declaration_received = BooleanField("Partner declaration received", validators=[DataRequired(message="Confirm the partner declaration before saving ShPP.")])
    notes = TextAreaField("Payroll Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save ShPP Input")


class PayrollSPBPInputForm(FlaskForm):
    """Capture one employee's parental-bereavement-pay input."""

    entitlement_reference = StringField(
        "Entitlement Reference",
        validators=[DataRequired(), Length(max=80)],
    )
    bereavement_date = DateField(
        "Bereavement Date",
        validators=[DataRequired()],
    )
    bereavement_pay_period_start = DateField(
        "Parental Bereavement Pay Period Start",
        validators=[DataRequired()],
    )
    average_weekly_earnings = DecimalField(
        "Average Weekly Earnings",
        places=2,
        validators=[
            InputRequired(),
            NumberRange(
                min=0,
                message="Average weekly earnings cannot be negative.",
            ),
        ],
    )
    paid_days = IntegerField(
        "SPBP Paid Days in this Period",
        validators=[
            InputRequired(),
            NumberRange(
                min=0,
                max=14,
                message="Enter between 0 and 14 paid days.",
            ),
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
        validators=[
            DataRequired(message="Confirm eligibility before saving SPBP.")
        ],
    )
    notice_received = BooleanField(
        "Employee notice received",
        validators=[DataRequired(message="Confirm notice before saving SPBP.")],
    )
    declaration_received = BooleanField(
        "Employee declaration received",
        validators=[
            DataRequired(message="Confirm the declaration before saving SPBP.")
        ],
    )
    notes = TextAreaField(
        "Payroll Notes",
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField("Save SPBP Input")


class PayrollSNCPInputForm(FlaskForm):
    """Capture one employee's neonatal-care-pay input."""

    entitlement_reference = StringField(
        "Entitlement Reference",
        validators=[DataRequired(), Length(max=80)],
    )
    baby_date_of_birth = DateField(
        "Baby Date of Birth",
        validators=[DataRequired()],
    )
    neonatal_care_start_date = DateField(
        "Neonatal Care Start Date",
        validators=[DataRequired()],
    )
    neonatal_care_through_date = DateField(
        "Neonatal Care Confirmed Through",
        validators=[DataRequired()],
    )
    neonatal_pay_period_start = DateField(
        "Neonatal Pay Period Start",
        validators=[DataRequired()],
    )
    average_weekly_earnings = DecimalField(
        "Average Weekly Earnings",
        places=2,
        validators=[
            InputRequired(),
            NumberRange(
                min=0,
                message="Average weekly earnings cannot be negative.",
            ),
        ],
    )
    paid_days = IntegerField(
        "SNCP Paid Days in this Period",
        validators=[
            InputRequired(),
            NumberRange(
                min=0,
                max=31,
                message="Enter between 0 and 31 paid days.",
            ),
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
        validators=[
            DataRequired(message="Confirm eligibility before saving SNCP.")
        ],
    )
    service_confirmed = BooleanField(
        "Continuous employment requirement confirmed",
        validators=[
            DataRequired(message="Confirm service before saving SNCP.")
        ],
    )
    neonatal_care_confirmed = BooleanField(
        "Qualifying neonatal care confirmed",
        validators=[
            DataRequired(message="Confirm neonatal care before saving SNCP.")
        ],
    )
    notice_received = BooleanField(
        "Employee notice received",
        validators=[DataRequired(message="Confirm notice before saving SNCP.")],
    )
    declaration_received = BooleanField(
        "Employee declaration received",
        validators=[
            DataRequired(message="Confirm the declaration before saving SNCP.")
        ],
    )
    notes = TextAreaField(
        "Payroll Notes",
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField("Save SNCP Input")
