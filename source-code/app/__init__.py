from flask import Flask, render_template
from flask_login import login_required
from config import Config
from app.extensions import db, login_manager, migrate
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

    # Configure Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        """Load the authenticated user from the database."""

        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    # Register authentication Blueprint
    from app.auth import auth_bp

    app.register_blueprint(auth_bp)

    @app.route("/")
    @login_required
    def home():
        return render_template("dashboard.html")

    return app
