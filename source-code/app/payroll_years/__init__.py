"""Payroll year blueprint."""

from flask import Blueprint


payroll_years_bp = Blueprint(
    "payroll_years",
    __name__,
    url_prefix="/payroll-years",
)


from app.payroll_years import routes

