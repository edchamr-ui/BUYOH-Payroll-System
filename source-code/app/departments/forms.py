from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class DepartmentForm(FlaskForm):
    name = StringField(
        "Department Name",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
    )

    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(max=500),
        ],
    )

    submit = SubmitField("Save Department")
