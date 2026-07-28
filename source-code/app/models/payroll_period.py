"""Payroll period database model."""

from datetime import datetime

from app.extensions import db


class PayrollPeriod(db.Model):
    """Represent a monthly payroll processing cycle."""

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
        server_default="Draft",
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

    locked_by = db.Column(
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

    locked_at = db.Column(
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

    locker = db.relationship(
        "User",
        foreign_keys=[locked_by],
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
        """Return the payroll period's human-readable name."""

        from calendar import month_name

        return (
            f"{month_name[self.month]} "
            f"{self.year}"
        )

    @property
    def is_draft(self):
        """Return whether the payroll period is a draft."""

        return self.status == "Draft"

    @property
    def is_processed(self):
        """Return whether payroll has been processed."""

        return self.status == "Processed"

    @property
    def is_approved(self):
        """Return whether payroll has been approved."""

        return self.status == "Approved"

    @property
    def is_locked(self):
        """Return whether the payroll period is locked."""

        return self.status == "Locked"

    @property
    def can_be_processed(self):
        """Return whether payroll processing is permitted."""

        return self.status in {
            "Draft",
            "Processed",
        }

    @property
    def can_be_approved(self):
        """Return whether the period can be approved."""

        return self.status == "Processed"

    @property
    def can_be_locked(self):
        """Return whether the period can be locked."""

        return self.status == "Approved"

    @property
    def can_be_reopened(self):
        """Return whether the period can be reopened."""

        return self.status == "Locked"

    def __repr__(self):
        """Return a developer-friendly model representation."""

        return (
            f"<PayrollPeriod "
            f"{self.month}/{self.year} "
            f"status={self.status}>"
        )
