"""Email Delivery Centre blueprint."""

from flask import Blueprint


email_deliveries_bp = Blueprint(
    "email_deliveries",
    __name__,
    url_prefix="/email-deliveries",
)


from app.email_deliveries import routes
