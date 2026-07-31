"""Authentication routes."""

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_user,
    logout_user,
)

from app.auth import auth_bp
from app.auth.forms import LoginForm
from app.models import User


@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():
    """Authenticate a user and start a session."""

    if current_user.is_authenticated:
        return redirect(
            url_for("home")
        )

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data.strip()

        user = User.query.filter_by(
            username=username
        ).first()

        if (
            user is None
            or not user.check_password(
                form.password.data
            )
        ):
            flash(
                "Invalid username or password.",
                "danger",
            )

            return render_template(
                "auth/login.html",
                form=form,
            )

        if not user.is_active:
            flash(
                "This account has been deactivated.",
                "danger",
            )

            return render_template(
                "auth/login.html",
                form=form,
            )

        login_user(
            user,
            remember=form.remember_me.data,
        )

        next_page = request.args.get("next")

        if (
            next_page
            and next_page.startswith("/")
            and not next_page.startswith("//")
        ):
            return redirect(next_page)

        return redirect(
            url_for("home")
        )

    return render_template(
        "auth/login.html",
        form=form,
    )


@auth_bp.route(
    "/logout",
    methods=["POST"],
)
def logout():
    """End the current authenticated session."""

    if current_user.is_authenticated:
        logout_user()

        flash(
            "You have been logged out successfully.",
            "success",
        )

    return redirect(
        url_for("auth.login")
    )

