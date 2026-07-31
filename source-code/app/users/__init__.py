"""User-management blueprint."""

from flask import Blueprint


users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/users",
)

from app.users import routes

