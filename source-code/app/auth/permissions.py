"""Role-based authorization decorators."""

from functools import wraps

from flask import abort
from flask_login import current_user


ADMIN = "Admin"
PAYROLL_OFFICER = "Payroll Officer"
MANAGEMENT = "Management"


def roles_required(*allowed_roles):
    """
    Restrict access to one or more roles.

    Example:

        @roles_required("Admin")

        @roles_required(
            "Admin",
            "Payroll Officer",
        )
    """

    def decorator(view):

        @wraps(view)
        def wrapped_view(*args, **kwargs):

            if not current_user.is_authenticated:
                abort(401)

            if current_user.role not in allowed_roles:
                abort(403)

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def admin_required(view):
    """Administrator only."""

    return roles_required(
        ADMIN,
    )(view)


def payroll_required(view):
    """
    Administrator and Payroll Officer.
    """

    return roles_required(
        ADMIN,
        PAYROLL_OFFICER,
    )(view)


def management_required(view):
    """
    Administrator and Management.
    """

    return roles_required(
        ADMIN,
        MANAGEMENT,
    )(view)


def authenticated_roles():
    """
    Convenience helper for templates.
    """

    if not current_user.is_authenticated:
        return []

    return {
        "is_admin":
            current_user.role == ADMIN,

        "is_payroll":
            current_user.role
            in (
                ADMIN,
                PAYROLL_OFFICER,
            ),

        "is_management":
            current_user.role
            in (
                ADMIN,
                MANAGEMENT,
            ),
    }

