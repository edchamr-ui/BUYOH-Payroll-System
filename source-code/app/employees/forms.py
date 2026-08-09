from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
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

from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


class EmployeeForm(FlaskForm):
    """Validate employee, payment method and banking information."""

    employee_number = StringField(
        "Employee Number",
        validators=[
            DataRequired(),
            Length(max=50),
        ],
    )

    first_name = StringField(
        "First Name",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
    )

    last_name = StringField(
        "Last Name",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
    )

    email = StringField(
        "Email Address",
       validators=[
           Optional(),
           Email(
               message="Enter a valid email address."
           ),
           Length(max=255),
        ],
    )



    national_id = StringField(
        "National ID",
        validators=[
            Optional(),
            Length(max=50),
        ],
    )

    job_title = StringField(
        "Job Title",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
    )

    department_id = SelectField(
        "Department",
        coerce=int,
        validators=[
            DataRequired(),
        ],
    )

    employment_date = DateField(
        "Employment Date",
        validators=[
            DataRequired(),
        ],
    )

    basic_salary = DecimalField(
        "Basic Salary",
        places=2,
        validators=[
            DataRequired(),
            NumberRange(min=0),
        ],
    )

    tax_residency = SelectField(
        "Tax Residency",
        choices=[
            ("Resident", "Resident"),
            ("Non-Resident", "Non-Resident"),
        ],
        default="Resident",
        validators=[DataRequired()],
    )

    employment_status = SelectField(
        "Employment Status",
        choices=[
            ("Active", "Active"),
            ("Probation", "Probation"),
            ("Suspended", "Suspended"),
            ("Terminated", "Terminated"),
        ],
        validators=[
            DataRequired(),
        ],
    )

    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("Cash", "Cash"),
            ("Bank Transfer", "Bank Transfer"),
        ],
        default="Cash",
        validators=[
            DataRequired(),
        ],
    )

    bank_name = StringField(
        "Bank Name",
        validators=[
            Optional(),
            Length(max=100),
        ],
    )

    bank_branch = StringField(
        "Bank Branch",
        validators=[
            Optional(),
            Length(max=100),
        ],
    )

    bank_code = StringField(
        "Bank Code",
        validators=[
            Optional(),
            Length(max=20),
        ],
    )

    account_name = StringField(
        "Account Name",
        validators=[
            Optional(),
            Length(max=150),
        ],
    )

    account_number = StringField(
        "Account Number",
        validators=[
            Optional(),
            Length(max=50),
        ],
    )

    account_type = SelectField(
        "Account Type",
        choices=[
            ("", "Select Account Type"),
            ("Current", "Current"),
            ("Savings", "Savings"),
            ("Cheque", "Cheque"),
            ("Other", "Other"),
        ],
        validators=[
            Optional(),
        ],
    )

    submit = SubmitField("Save Employee")

    def validate_bank_name(self, field):
        """Require a bank name for bank-transfer employees."""

        if (
            self.payment_method.data == "Bank Transfer"
            and not field.data
        ):
            raise ValidationError(
                "Bank name is required for bank transfers."
            )

    def validate_account_name(self, field):
        """Require an account name for bank-transfer employees."""

        if (
            self.payment_method.data == "Bank Transfer"
            and not field.data
        ):
            raise ValidationError(
                "Account name is required for bank transfers."
            )

    def validate_account_number(self, field):
        """Require an account number for bank-transfer employees."""

        if (
            self.payment_method.data == "Bank Transfer"
            and not field.data
        ):
            raise ValidationError(
                "Account number is required for bank transfers."
            )
