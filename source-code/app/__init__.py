"""BUYOH Payroll application factory."""

from flask import Flask, render_template
from flask_login import login_required

from config import Config

from app.cli import register_cli_commands
from app.extensions import (
    db,
    login_manager,
    migrate,
)
from app.models import (
    Allowance,
    AuditLog,
    Deduction,
    Department,
    Employee,
    PayrollPeriod,
    PayrollRecord,
    Payslip,
    Setting,
    User,
)


def create_app():
    """Create and configure the BUYOH Payroll Flask application."""

    app = Flask(__name__)

    # Load configuration from config.py and .env
    app.config.from_object(Config)

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register Flask CLI management commands
    register_cli_commands(app)

    # Configure Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = (
        "Please log in to access this page."
    )
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        """Load the authenticated user from the database."""

        try:
            return db.session.get(
                User,
                int(user_id),
            )

        except (TypeError, ValueError):
            return None

    # Register authentication blueprint
    from app.auth import auth_bp

    app.register_blueprint(auth_bp)

    # Register employees blueprint
    from app.employees import employees_bp

    app.register_blueprint(employees_bp)

    # Register departments blueprint
    from app.departments import departments_bp

    app.register_blueprint(departments_bp)

    # Register payroll periods blueprint
    from app.payroll_periods import payroll_periods_bp

    app.register_blueprint(payroll_periods_bp)

    # Register payroll blueprint
    from app.payroll import payroll_bp

    app.register_blueprint(payroll_bp)

    # Register payslips blueprint
    from app.payslips import payslips_bp

    app.register_blueprint(payslips_bp)

    # Register reports blueprint
    from app.reports import reports_bp

    app.register_blueprint(reports_bp)

    @app.route("/")
    @login_required
    def home():
        """Display live payroll dashboard statistics."""

        employee_count = Employee.query.filter_by(
            is_active=True,
        ).count()

        department_count = Department.query.count()

        latest_payroll_period = (
            PayrollPeriod.query
            .order_by(
                PayrollPeriod.year.desc(),
                PayrollPeriod.month.desc(),
            )
            .first()
        )

        if latest_payroll_period:
            current_payroll_status = (
                latest_payroll_period.status
            )
        else:
            current_payroll_status = "No Period"

        payslip_count = Payslip.query.count()

        return render_template(
            "dashboard.html",
            employee_count=employee_count,
            department_count=department_count,
            current_payroll_status=(
                current_payroll_status
            ),
            payslip_count=payslip_count,
        )

    return app
