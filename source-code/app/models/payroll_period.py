from datetime import datetime

from app.extensions import db


class PayrollPeriod(db.Model):
    """Represents a monthly payroll processing cycle."""

    __tablename__ = "payroll_periods"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    month = db.Column(
        db.Integer,
        nullable=False,
    )

    year = db.Column(
        db.Integer,
        nullable=False,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Draft",
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
    )

    approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    approved_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    creator = db.relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_payroll_periods",
    )

    approver = db.relationship(
        "User",
        foreign_keys=[approved_by],
        back_populates="approved_payroll_periods",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "month",
            "year",
            name="uq_payroll_period_month_year",
        ),
        db.CheckConstraint(
            "month >= 1 AND month <= 12",
            name="ck_payroll_period_valid_month",
        ),
    )

    def __repr__(self):
        return f"<PayrollPeriod {self.month}/{self.year}>"

