from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class EmployeeForm(FlaskForm):
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
        validators=[DataRequired()],
    )

    employment_date = DateField(
        "Employment Date",
        validators=[DataRequired()],
    )

    basic_salary = DecimalField(
        "Basic Salary",
        places=2,
        validators=[
            DataRequired(),
            NumberRange(min=0),
        ],
    )

    employment_status = SelectField(
        "Employment Status",
        choices=[
            ("Active", "Active"),
            ("Probation", "Probation"),
            ("Suspended", "Suspended"),
            ("Terminated", "Terminated"),
        ],
        validators=[DataRequired()],
    )

    submit = SubmitField("Save Employee")
