from flask import Blueprint


payroll_bp = Blueprint(
    "payroll",
    __name__,
    url_prefix="/payroll",
)



from app.payroll import routes
from app.payroll import year_routes
from app.payroll import year_end_routes
