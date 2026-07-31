"""Forms for company and payroll settings."""

from flask_wtf import FlaskForm
from flask_wtf.file import (
    FileAllowed,
    FileField,
)
from wtforms import (
    BooleanField,
    DecimalField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    NumberRange,
    Optional,
    URL,
)


class CompanySettingsForm(FlaskForm):
    """Manage company identity and payroll defaults."""

    company_name = StringField(
        "Registered Company Name",
        validators=[
            DataRequired(),
            Length(max=150),
        ],
    )

    trading_name = StringField(
        "Trading Name",
        validators=[
            Optional(),
            Length(max=150),
        ],
    )

    registration_number = StringField(
        "Company Registration Number",
        validators=[
            Optional(),
            Length(max=100),
        ],
    )

    tax_number = StringField(
        "Company Tax Number",
        validators=[
            Optional(),
            Length(max=100),
        ],
    )

    nssa_employer_number = StringField(
        "NSSA Employer Number",
        validators=[
            Optional(),
            Length(max=100),
        ],
    )

    physical_address = TextAreaField(
        "Physical Address",
        validators=[
            Optional(),
            Length(max=500),
        ],
    )

    postal_address = TextAreaField(
        "Postal Address",
        validators=[
            Optional(),
            Length(max=500),
        ],
    )

    phone = StringField(
        "Telephone Number",
        validators=[
            Optional(),
            Length(max=50),
        ],
    )

    email = StringField(
        "Company Email",
        validators=[
            Optional(),
            Email(),
            Length(max=150),
        ],
    )

    website = StringField(
        "Website",
        validators=[
            Optional(),
            URL(),
            Length(max=200),
        ],
    )

    currency = SelectField(
        "Default Currency",
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
            DataRequired(),
        ],
    )

    payroll_country = SelectField(
        "Payroll Country",
        choices=[
            (
                "Zimbabwe",
                "Zimbabwe",
            ),
        ],
        validators=[
            DataRequired(),
        ],
    )

    default_payment_day = IntegerField(
        "Default Payroll Payment Day",
        validators=[
            DataRequired(),
            NumberRange(
                min=1,
                max=31,
                message=(
                    "Payment day must be between "
                    "1 and 31."
                ),
            ),
        ],
    )

    company_logo = FileField(
        "Company Logo",
        validators=[
            Optional(),
            FileAllowed(
                [
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                ],
                (
                    "Upload a PNG, JPG, JPEG "
                    "or WebP image."
                ),
            ),
        ],
    )

    remove_company_logo = BooleanField(
        "Remove the current company logo",
    )

    payslip_footer = TextAreaField(
        "Payslip Footer",
        validators=[
            Optional(),
            Length(max=1000),
        ],
    )

    payslip_email_subject = StringField(
        "Default Payslip Email Subject",
        validators=[
            DataRequired(),
            Length(max=255),
        ],
    )

    payslip_email_message = TextAreaField(
        "Default Payslip Email Message",
        validators=[
            DataRequired(),
            Length(max=3000),
        ],
    )

    submit = SubmitField(
        "Save Company Settings",
    )


class AllowanceTypeForm(FlaskForm):
    """Create or update a reusable allowance type."""

    allowance_type_id = HiddenField(
        "Allowance Type ID",
        validators=[
            Optional(),
        ],
    )

    name = StringField(
        "Allowance Name",
        validators=[
            DataRequired(),
            Length(
                min=2,
                max=120,
            ),
        ],
    )

    code = StringField(
        "Allowance Code",
        validators=[
            DataRequired(),
            Length(
                min=2,
                max=40,
            ),
        ],
    )

    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(max=1000),
        ],
    )

    calculation_method = SelectField(
        "Calculation Method",
        choices=[
            (
                "Fixed Amount",
                "Fixed Amount",
            ),
            (
                "Percentage",
                "Percentage of Basic Salary",
            ),
        ],
        validators=[
            DataRequired(),
        ],
    )

    default_amount = DecimalField(
        "Default Amount",
        places=2,
        default=0,
        validators=[
            Optional(),
            NumberRange(
                min=0,
                message=(
                    "Default amount cannot be negative."
                ),
            ),
        ],
    )

    default_percentage = DecimalField(
        "Default Percentage",
        places=4,
        default=0,
        validators=[
            Optional(),
            NumberRange(
                min=0,
                max=100,
                message=(
                    "Percentage must be between "
                    "0 and 100."
                ),
            ),
        ],
    )

    is_taxable = BooleanField(
        "Include in taxable earnings",
        default=True,
    )

    is_recurring = BooleanField(
        "Recurring allowance",
        default=True,
    )

    is_active = BooleanField(
        "Active",
        default=True,
    )

    submit = SubmitField(
        "Save Allowance Type",
    )


class DeductionTypeForm(FlaskForm):
    """Create or update a reusable deduction type."""

    deduction_type_id = HiddenField(
        "Deduction Type ID",
        validators=[
            Optional(),
        ],
    )

    name = StringField(
        "Deduction Name",
        validators=[
            DataRequired(),
            Length(
                min=2,
                max=120,
            ),
        ],
    )

    code = StringField(
        "Deduction Code",
        validators=[
            DataRequired(),
            Length(
                min=2,
                max=40,
            ),
        ],
    )

    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(max=1000),
        ],
    )

    category = SelectField(
        "Category",
        choices=[
            (
                "Statutory",
                "Statutory",
            ),
            (
                "Voluntary",
                "Voluntary",
            ),
            (
                "Loan",
                "Loan",
            ),
            (
                "Garnishee",
                "Garnishee",
            ),
            (
                "Other",
                "Other",
            ),
        ],
        validators=[
            DataRequired(),
        ],
    )

    calculation_method = SelectField(
        "Calculation Method",
        choices=[
            (
                "Fixed Amount",
                "Fixed Amount",
            ),
            (
                "Percentage",
                "Percentage of Basic Salary",
            ),
        ],
        validators=[
            DataRequired(),
        ],
    )

    default_amount = DecimalField(
        "Default Employee Amount",
        places=2,
        default=0,
        validators=[
            Optional(),
            NumberRange(
                min=0,
                message=(
                    "Default amount cannot be negative."
                ),
            ),
        ],
    )

    default_percentage = DecimalField(
        "Default Employee Percentage",
        places=4,
        default=0,
        validators=[
            Optional(),
            NumberRange(
                min=0,
                max=100,
                message=(
                    "Percentage must be between "
                    "0 and 100."
                ),
            ),
        ],
    )

    employer_percentage = DecimalField(
        "Default Employer Percentage",
        places=4,
        default=0,
        validators=[
            Optional(),
            NumberRange(
                min=0,
                max=100,
                message=(
                    "Employer percentage must be between "
                    "0 and 100."
                ),
            ),
        ],
    )

    is_statutory = BooleanField(
        "Statutory deduction or contribution",
        default=False,
    )

    reduces_net_pay = BooleanField(
        "Deduct from employee net pay",
        default=True,
    )

    is_recurring = BooleanField(
        "Recurring deduction",
        default=True,
    )

    is_active = BooleanField(
        "Active",
        default=True,
    )

    submit = SubmitField(
        "Save Deduction Type",
    )
