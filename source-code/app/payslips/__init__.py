"""Payslips blueprint."""

from flask import Blueprint


payslips_bp = Blueprint(
    "payslips",
    __name__,
    url_prefix="/payslips",
)


from app.payslips import routes
