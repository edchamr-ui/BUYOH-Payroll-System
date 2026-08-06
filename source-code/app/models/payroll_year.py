"""Payroll year database model."""

from datetime import datetime

from app.extensions import db


class PayrollYear(db.Model):
    """Represent one controlled payroll year lifecycle."""

    __tablename__ = "payroll_years"

    STATUS_OPEN = "Open"
    STATUS_CLOSING = "Closing"
    STATUS_CLOSED = "Closed"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, unique=True, index=True)

    status = db.Column(
        db.String(20),
        nullable=False,
        default=STATUS_OPEN,
        server_default=STATUS_OPEN,
        index=True,
    )

    opened_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    opened_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    closing_started_at = db.Column(db.DateTime, nullable=True)

    closing_started_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    closed_at = db.Column(db.DateTime, nullable=True)

    closed_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    closing_reason = db.Column(db.Text, nullable=True)

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

    opened_by_user = db.relationship(
        "User",
        foreign_keys=[opened_by_user_id],
        lazy="select",
    )

    closing_started_by_user = db.relationship(
        "User",
        foreign_keys=[closing_started_by_user_id],
        lazy="select",
    )

    closed_by_user = db.relationship(
        "User",
        foreign_keys=[closed_by_user_id],
        lazy="select",
    )

    payroll_periods = db.relationship(
        "PayrollPeriod",
        back_populates="payroll_year",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="PayrollPeriod.month",
    )

    __table_args__ = (
        db.CheckConstraint(
            "year >= 2020 AND year <= 2100",
            name="ck_payroll_year_valid_year",
        ),
        db.CheckConstraint(
            "status IN ('Open', 'Closing', 'Closed')",
            name="ck_payroll_year_valid_status",
        ),
    )

    @property
    def is_open(self):
        return self.status == self.STATUS_OPEN

    @property
    def is_closing(self):
        return self.status == self.STATUS_CLOSING

    @property
    def is_closed(self):
        return self.status == self.STATUS_CLOSED

    @property
    def period_count(self):
        return len(self.payroll_periods)

    @property
    def locked_period_count(self):
        return sum(
            1
            for period in self.payroll_periods
            if period.is_locked
        )

    @property
    def all_periods_locked(self):
        return (
            self.period_count == 12
            and self.locked_period_count == 12
        )

    def __repr__(self):
        return (
            f"<PayrollYear "
            f"year={self.year} "
            f"status={self.status!r}>"
        )

