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

    start_date = db.Column(
        db.Date,
        nullable=False,
    )

    end_date = db.Column(
        db.Date,
        nullable=False,
    )

    payment_date = db.Column(
        db.Date,
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

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    payroll_records = db.relationship(
        "PayrollRecord",
        back_populates="payroll_period",
        lazy="select",
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
        db.CheckConstraint(
            "end_date >= start_date",
            name="ck_payroll_period_valid_date_range",
        ),
    )

    @property
    def period_name(self):
        """Return a human-readable period name."""

        from calendar import month_name

        return f"{month_name[self.month]} {self.year}"

    @property
    def is_locked(self):
        """Return whether the payroll period is locked."""

        return self.status == "Locked"

    def __repr__(self):
        return f"<PayrollPeriod {self.month}/{self.year}>"
