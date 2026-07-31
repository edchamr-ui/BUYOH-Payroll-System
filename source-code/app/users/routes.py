"""Administrator routes for managing system users."""

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.auth.permissions import admin_required
from app.extensions import db
from app.models import User
from app.users import users_bp
from app.users.forms import (
    CreateUserForm,
    EditUserForm,
    ResetPasswordForm,
    UserActionForm,
)


@users_bp.route("/")
@login_required
@admin_required
def index():
    """Display searchable and paginated users."""

    search_term = request.args.get(
        "q",
        "",
    ).strip()

    role_filter = request.args.get(
        "role",
        "",
    ).strip()

    status_filter = request.args.get(
        "status",
        "all",
    ).strip().lower()

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    query = User.query

    if search_term:
        search_pattern = f"%{search_term}%"

        query = query.filter(
            or_(
                User.username.ilike(
                    search_pattern
                ),
                User.email.ilike(
                    search_pattern
                ),
                User.first_name.ilike(
                    search_pattern
                ),
                User.last_name.ilike(
                    search_pattern
                ),
            )
        )

    if role_filter in {
        "Admin",
        "Payroll Officer",
        "Management",
    }:
        query = query.filter(
            User.role == role_filter
        )

    if status_filter == "active":
        query = query.filter(
            User.is_active.is_(True)
        )

    elif status_filter == "inactive":
        query = query.filter(
            User.is_active.is_(False)
        )

    pagination = (
        query
        .order_by(
            User.first_name.asc(),
            User.last_name.asc(),
            User.username.asc(),
        )
        .paginate(
            page=page,
            per_page=20,
            error_out=False,
        )
    )

    total_users = User.query.count()

    active_users = User.query.filter(
        User.is_active.is_(True)
    ).count()

    admin_count = User.query.filter(
        User.role == "Admin"
    ).count()

    action_form = UserActionForm()

    return render_template(
        "users/index.html",
        users=pagination.items,
        pagination=pagination,
        search_term=search_term,
        role_filter=role_filter,
        status_filter=status_filter,
        total_users=total_users,
        active_users=active_users,
        admin_count=admin_count,
        action_form=action_form,
    )


@users_bp.route(
    "/add",
    methods=["GET", "POST"],
)
@login_required
@admin_required
def add_user():
    """Create a system user."""

    form = CreateUserForm()

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        existing_username = User.query.filter(
            db.func.lower(User.username)
            == username.lower()
        ).first()

        if existing_username:
            flash(
                "That username is already in use.",
                "danger",
            )

            return render_template(
                "users/form.html",
                form=form,
                page_heading="Add User",
                page_description=(
                    "Create an account and assign its role."
                ),
            )

        existing_email = User.query.filter(
            db.func.lower(User.email)
            == email.lower()
        ).first()

        if existing_email:
            flash(
                "That email address is already in use.",
                "danger",
            )

            return render_template(
                "users/form.html",
                form=form,
                page_heading="Add User",
                page_description=(
                    "Create an account and assign its role."
                ),
            )

        user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            username=username,
            email=email,
            role=form.role.data,
            is_active=form.is_active.data,
        )

        user.set_password(
            form.password.data
        )

        db.session.add(user)

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "The user could not be created because "
                    "the username or email already exists."
                ),
                "danger",
            )

            return render_template(
                "users/form.html",
                form=form,
                page_heading="Add User",
                page_description=(
                    "Create an account and assign its role."
                ),
            )

        flash(
            (
                f"User {user.full_name} was created "
                "successfully."
            ),
            "success",
        )

        return redirect(
            url_for("users.index")
        )

    return render_template(
        "users/form.html",
        form=form,
        page_heading="Add User",
        page_description=(
            "Create an account and assign its role."
        ),
    )


@users_bp.route(
    "/<int:user_id>/edit",
    methods=["GET", "POST"],
)
@login_required
@admin_required
def edit_user(user_id):
    """Edit an existing system user."""

    user = User.query.get_or_404(
        user_id
    )

    form = EditUserForm(
        obj=user
    )

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        requested_role = form.role.data
        requested_active_status = (
            form.is_active.data
        )

        username_owner = (
            User.query
            .filter(
                db.func.lower(User.username)
                == username.lower(),
                User.id != user.id,
            )
            .first()
        )

        if username_owner:
            flash(
                "That username is already in use.",
                "danger",
            )

            return render_template(
                "users/form.html",
                form=form,
                user=user,
                page_heading="Edit User",
                page_description=(
                    "Update account details and permissions."
                ),
            )

        email_owner = (
            User.query
            .filter(
                db.func.lower(User.email)
                == email.lower(),
                User.id != user.id,
            )
            .first()
        )

        if email_owner:
            flash(
                "That email address is already in use.",
                "danger",
            )

            return render_template(
                "users/form.html",
                form=form,
                user=user,
                page_heading="Edit User",
                page_description=(
                    "Update account details and permissions."
                ),
            )

        if user.id == current_user.id:
            if not requested_active_status:
                flash(
                    "You cannot deactivate your own account.",
                    "danger",
                )

                return render_template(
                    "users/form.html",
                    form=form,
                    user=user,
                    page_heading="Edit User",
                    page_description=(
                        "Update account details and permissions."
                    ),
                )

            if requested_role != "Admin":
                flash(
                    (
                        "You cannot remove the Admin role "
                        "from your own account."
                    ),
                    "danger",
                )

                return render_template(
                    "users/form.html",
                    form=form,
                    user=user,
                    page_heading="Edit User",
                    page_description=(
                        "Update account details and permissions."
                    ),
                )

        if (
            user.role == "Admin"
            and requested_role != "Admin"
        ):
            active_admin_count = User.query.filter(
                User.role == "Admin",
                User.is_active.is_(True),
            ).count()

            if active_admin_count <= 1:
                flash(
                    (
                        "The final active Administrator "
                        "cannot be reassigned."
                    ),
                    "danger",
                )

                return render_template(
                    "users/form.html",
                    form=form,
                    user=user,
                    page_heading="Edit User",
                    page_description=(
                        "Update account details and permissions."
                    ),
                )

        user.first_name = (
            form.first_name.data.strip()
        )

        user.last_name = (
            form.last_name.data.strip()
        )

        user.username = username
        user.email = email
        user.role = requested_role
        user.is_active = requested_active_status

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "The changes could not be saved because "
                    "the username or email already exists."
                ),
                "danger",
            )

            return render_template(
                "users/form.html",
                form=form,
                user=user,
                page_heading="Edit User",
                page_description=(
                    "Update account details and permissions."
                ),
            )

        flash(
            "User updated successfully.",
            "success",
        )

        return redirect(
            url_for("users.index")
        )

    return render_template(
        "users/form.html",
        form=form,
        user=user,
        page_heading="Edit User",
        page_description=(
            "Update account details and permissions."
        ),
    )


@users_bp.route(
    "/<int:user_id>/toggle-status",
    methods=["POST"],
)
@login_required
@admin_required
def toggle_user_status(user_id):
    """Activate or deactivate a user account."""

    user = User.query.get_or_404(
        user_id
    )

    form = UserActionForm()

    if not form.validate_on_submit():
        flash(
            "The account-status request was invalid.",
            "danger",
        )

        return redirect(
            url_for("users.index")
        )

    if user.id == current_user.id:
        flash(
            "You cannot deactivate your own account.",
            "danger",
        )

        return redirect(
            url_for("users.index")
        )

    if (
        user.role == "Admin"
        and user.is_active
    ):
        active_admin_count = User.query.filter(
            User.role == "Admin",
            User.is_active.is_(True),
        ).count()

        if active_admin_count <= 1:
            flash(
                (
                    "The final active Administrator "
                    "cannot be deactivated."
                ),
                "danger",
            )

            return redirect(
                url_for("users.index")
            )

    user.is_active = not user.is_active

    db.session.commit()

    if user.is_active:
        message = "User account activated successfully."
    else:
        message = "User account deactivated successfully."

    flash(
        message,
        "success",
    )

    return redirect(
        url_for("users.index")
    )


@users_bp.route(
    "/<int:user_id>/reset-password",
    methods=["GET", "POST"],
)
@login_required
@admin_required
def reset_password(user_id):
    """Set a new temporary password for a user."""

    user = User.query.get_or_404(
        user_id
    )

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(
            form.password.data
        )

        db.session.commit()

        flash(
            (
                f"The password for {user.full_name} "
                "was reset successfully."
            ),
            "success",
        )

        return redirect(
            url_for("users.index")
        )

    return render_template(
        "users/reset_password.html",
        form=form,
        user=user,
    )
