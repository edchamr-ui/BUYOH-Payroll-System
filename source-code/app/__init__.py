"""BUYOH Payroll application factory."""

from decimal import Decimal

from flask import Flask, render_template
from flask_login import login_required
from sqlalchemy import func

from config import Config
from app.cli import register_cli_commands
from app.extensions import db, login_manager, migrate
from app.health import health_bp
from app.security import register_security_headers, validate_runtime_config
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
from app.payroll_years import payroll_years_bp
from app.services.company_settings_service import (
    CompanySettingsService,
)


def create_app(config_overrides=None):
    """Create and configure the payroll Flask application."""

    app = Flask(__name__)
    app.config.from_object(Config)

    if config_overrides:
        app.config.update(config_overrides)

    validate_runtime_config(app)
    register_security_headers(app)

    app.register_blueprint(health_bp)

    app.register_blueprint(
        payroll_years_bp
    )

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    register_cli_commands(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = (
        "Please log in to access this page."
    )
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        """Load the authenticated user."""

        try:
            return db.session.get(
                User,
                int(user_id),
            )

        except (TypeError, ValueError):
            return None

    @app.errorhandler(403)
    def forbidden(_error):
        """Display a friendly access-denied page."""

        return (
            render_template("errors/403.html"),
            403,
        )

    @app.context_processor
    def inject_company_settings():
        """Make company settings available in all templates."""

        return {
            "company_settings": (
                CompanySettingsService.get_company_profile()
            )
        }

    from app.auth import auth_bp
    from app.employees import employees_bp
    from app.departments import departments_bp
    from app.payroll_periods import payroll_periods_bp
    from app.payroll import payroll_bp
    from app.payslips import payslips_bp
    from app.reports import reports_bp
    from app.audit_logs import audit_logs_bp
    from app.email_deliveries import email_deliveries_bp
    from app.users import users_bp
    from app.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(payroll_periods_bp)
    app.register_blueprint(payroll_bp)
    app.register_blueprint(payslips_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_logs_bp)
    app.register_blueprint(email_deliveries_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)

    @app.route("/")
    @login_required
    def home():
        """Display the executive payroll dashboard."""

        zero = Decimal("0.00")

        employee_count = Employee.query.filter_by(
            is_active=True
        ).count()

        department_count = Department.query.filter_by(
            is_active=True
        ).count()

        latest_payroll_period = (
            PayrollPeriod.query
            .order_by(
                PayrollPeriod.year.desc(),
                PayrollPeriod.month.desc(),
            )
            .first()
        )

        payroll_summary = {
            "gross_pay": zero,
            "net_pay": zero,
            "total_deductions": zero,
            "paye": zero,
            "nssa": zero,
            "aids_levy": zero,
            "employer_cost": zero,
            "record_count": 0,
        }

        current_period_payslip_count = 0

        if latest_payroll_period:
            summary = (
                db.session.query(
                    func.coalesce(
                        func.sum(PayrollRecord.gross_pay),
                        0,
                    ),
                    func.coalesce(
                        func.sum(PayrollRecord.net_pay),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            PayrollRecord.total_deductions
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(PayrollRecord.paye),
                        0,
                    ),
                    func.coalesce(
                        func.sum(PayrollRecord.nssa),
                        0,
                    ),
                    func.coalesce(
                        func.sum(PayrollRecord.aids_levy),
                        0,
                    ),
                    func.coalesce(
                        func.sum(PayrollRecord.employer_cost),
                        0,
                    ),
                    func.count(PayrollRecord.id),
                )
                .filter(
                    PayrollRecord.payroll_period_id
                    == latest_payroll_period.id
                )
                .one()
            )

            payroll_summary = {
                "gross_pay": summary[0] or zero,
                "net_pay": summary[1] or zero,
                "total_deductions": summary[2] or zero,
                "paye": summary[3] or zero,
                "nssa": summary[4] or zero,
                "aids_levy": summary[5] or zero,
                "employer_cost": summary[6] or zero,
                "record_count": summary[7] or 0,
            }

            current_period_payslip_count = (
                Payslip.query
                .join(
                    PayrollRecord,
                    Payslip.payroll_record_id
                    == PayrollRecord.id,
                )
                .filter(
                    PayrollRecord.payroll_period_id
                    == latest_payroll_period.id
                )
                .count()
            )

        recent_activity = (
            AuditLog.query
            .order_by(
                AuditLog.created_at.desc()
            )
            .limit(8)
            .all()
        )

        return render_template(
            "dashboard.html",
            employee_count=employee_count,
            department_count=department_count,
            latest_payroll_period=latest_payroll_period,
            payroll_summary=payroll_summary,
            current_period_payslip_count=(
                current_period_payslip_count
            ),
            recent_activity=recent_activity,
        )

    return app
