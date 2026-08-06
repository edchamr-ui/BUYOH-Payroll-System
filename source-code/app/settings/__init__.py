"""Company and payroll settings blueprint."""

from flask import Blueprint


settings_bp = Blueprint(
    "settings",
    __name__,
    url_prefix="/settings",
)


# Core company, allowance and deduction settings.
from app.settings import routes

# Operational statutory rule sets.
from app.settings import statutory_routes

# Database-backed statutory preset library.
from app.settings import statutory_library_routes

# PAYE tax-band management and calculation preview.
from app.settings import statutory_taxband_routes

# Administrator-only payroll reset centre.
from app.settings import reset_routes


from app.settings import statutory_update_routes


from app.settings import statutory_adoption_routes


from app.settings import statutory_history_routes

from app.settings import statutory_rollback_routes
