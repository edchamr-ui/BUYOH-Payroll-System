"""Forms for administrator user management."""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
)


ROLE_CHOICES = [
    ("Admin", "Administrator"),
    ("Payroll Officer", "Payroll Officer"),
    ("Management", "Management"),
]


class CreateUserForm(FlaskForm):
    """Create a new application user."""

    first_name = StringField(
        "First Name",
        validators=[
            DataRequired(),
            Length(max=50),
        ],
    )

    last_name = StringField(
        "Last Name",
        validators=[
            DataRequired(),
            Length(max=50),
        ],
    )

    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=50),
        ],
    )

    email = StringField(
        "Work Email",
        validators=[
            DataRequired(),
            Email(),
            Length(max=120),
        ],
    )

    role = SelectField(
        "Role",
        choices=ROLE_CHOICES,
        validators=[
            DataRequired(),
        ],
    )

    password = PasswordField(
        "Temporary Password",
        validators=[
            DataRequired(),
            Length(min=8, max=128),
        ],
    )

    confirm_password = PasswordField(
        "Confirm Temporary Password",
        validators=[
            DataRequired(),
            EqualTo(
                "password",
                message="The passwords must match.",
            ),
        ],
    )

    is_active = BooleanField(
        "Account is active",
        default=True,
    )

    submit = SubmitField(
        "Create User",
    )


class EditUserForm(FlaskForm):
    """Edit an existing application user."""

    first_name = StringField(
        "First Name",
        validators=[
            DataRequired(),
            Length(max=50),
        ],
    )

    last_name = StringField(
        "Last Name",
        validators=[
            DataRequired(),
            Length(max=50),
        ],
    )

    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=50),
        ],
    )

    email = StringField(
        "Work Email",
        validators=[
            DataRequired(),
            Email(),
            Length(max=120),
        ],
    )

    role = SelectField(
        "Role",
        choices=ROLE_CHOICES,
        validators=[
            DataRequired(),
        ],
    )

    is_active = BooleanField(
        "Account is active",
    )

    submit = SubmitField(
        "Save Changes",
    )


class ResetPasswordForm(FlaskForm):
    """Set a new temporary password."""

    password = PasswordField(
        "New Temporary Password",
        validators=[
            DataRequired(),
            Length(min=8, max=128),
        ],
    )

    confirm_password = PasswordField(
        "Confirm Temporary Password",
        validators=[
            DataRequired(),
            EqualTo(
                "password",
                message="The passwords must match.",
            ),
        ],
    )

    submit = SubmitField(
        "Reset Password",
    )


class UserActionForm(FlaskForm):
    """Validate account status-change requests."""

    submit = SubmitField(
        "Submit",
    )

