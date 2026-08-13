"""Application user model."""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.time_utils import legacy_utc_now


class User(UserMixin, db.Model):
    """Represents a user who can access the BUYOH Payroll System."""

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    first_name = db.Column(
        db.String(50),
        nullable=True,
    )

    last_name = db.Column(
        db.String(50),
        nullable=True,
    )

    role = db.Column(
        db.String(20),
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=legacy_utc_now,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=legacy_utc_now,
        onupdate=legacy_utc_now,
    )

    created_payroll_periods = db.relationship(
        "PayrollPeriod",
        foreign_keys="PayrollPeriod.created_by",
        back_populates="creator",
        lazy="select",
    )

    approved_payroll_periods = db.relationship(
        "PayrollPeriod",
        foreign_keys="PayrollPeriod.approved_by",
        back_populates="approver",
        lazy="select",
    )

    processed_payroll_records = db.relationship(
        "PayrollRecord",
        back_populates="processor",
        lazy="select",
    )

    generated_payslips = db.relationship(
        "Payslip",
        back_populates="generator",
        lazy="select",
    )

    sent_email_deliveries = db.relationship(
        "EmailDelivery",
        back_populates="sender",
        lazy="dynamic",
        foreign_keys="EmailDelivery.sent_by_id",
    )

    audit_logs = db.relationship(
        "AuditLog",
        back_populates="user",
        lazy="select",
    )

    updated_settings = db.relationship(
        "Setting",
        back_populates="updater",
        lazy="select",
    )

    def set_password(self, password):
        """Hash and store the user's password."""

        if not password:
            raise ValueError("Password cannot be empty.")

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check a plaintext password against the stored hash."""

        if not self.password_hash or not password:
            return False

        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        """Return the user's full name, or username when unavailable."""

        names = [self.first_name, self.last_name]
        full_name = " ".join(name for name in names if name)

        return full_name or self.username

    def __repr__(self):
        return f"<User {self.username}>"
