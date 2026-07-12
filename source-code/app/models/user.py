from datetime import datetime

from app.extensions import db


class User(db.Model):
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
        default=datetime.utcnow,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    def __repr__(self):
        return f"<User {self.username}>"
