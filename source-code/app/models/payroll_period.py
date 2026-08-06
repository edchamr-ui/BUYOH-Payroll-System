"""Payroll period database model."""

from datetime import datetime

from app.extensions import db


class PayrollPeriod(db.Model):
    """Represent a monthly payroll processing cycle."""

    __tablename__ = "payroll_periods"

    id = db.Column(db.Integer, primary_key=True)

    payroll_year_id = db.Column(
        db.Integer,
        db.ForeignKey("payroll_years.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)

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

    approved_at = db.Column(db.DateTime, nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)

    payroll_year = db.relationship(
        "PayrollYear",
        back_populates="payroll_periods",
        lazy="select",
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
        db.UniqueConstraint(
            "payroll_year_id",
            "month",
            name="uq_payroll_period_year_month",
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
        from calendar import month_name
        return f"{month_name[self.month]} {self.year}"

    @property
    def is_draft(self):
        return self.status == "Draft"

    @property
    def is_processed(self):
        return self.status == "Processed"

    @property
    def is_approved(self):
        return self.status == "Approved"

    @property
    def is_locked(self):
        return self.status == "Locked"

    @property
    def can_be_processed(self):
        return (
            self.status in {"Draft", "Processed"}
            and self.payroll_year is not None
            and self.payroll_year.is_open
        )

    @property
    def can_be_approved(self):
        return (
            self.status == "Processed"
            and self.payroll_year is not None
            and self.payroll_year.is_open
        )

    @property
    def can_be_locked(self):
        return (
            self.status == "Approved"
            and self.payroll_year is not None
            and self.payroll_year.is_open
        )

    @property
    def can_be_reopened(self):
        return (
            self.status == "Locked"
            and self.payroll_year is not None
            and self.payroll_year.is_open
        )

    def __repr__(self):
        return (
            f"<PayrollPeriod "
            f"{self.month}/{self.year} "
            f"status={self.status}>"
        )

