from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user

from app.auth import auth_bp
from app.auth.forms import LoginForm
from app.models import User


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            username=form.username.data.strip()
        ).first()

        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_active:
            flash("This account has been deactivated.", "danger")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        return redirect(url_for("home"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "success")

    return redirect(url_for("auth.login"))
