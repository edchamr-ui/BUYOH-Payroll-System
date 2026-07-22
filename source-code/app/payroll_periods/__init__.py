from flask import Blueprint


payroll_periods_bp = Blueprint(
    "payroll_periods",
    __name__,
    url_prefix="/payroll-periods",
)


from app.payroll_periods import routes
