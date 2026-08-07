from flask import render_template

from flask_login import login_required

from app.auth.permissions import admin_required

from app.statutory_builder import (
    statutory_builder_bp,
)


@statutory_builder_bp.route("/")
@login_required
@admin_required
def index():
    """
    Statutory Package Builder home.
    """

    return render_template(
        "statutory_builder/index.html",
    )


@statutory_builder_bp.route("/new")
@login_required
@admin_required
def new_package():

    return render_template(
        "statutory_builder/wizard_step1.html",
    )
