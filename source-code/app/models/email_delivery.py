"""Email delivery history model."""

from datetime import datetime

from app.extensions import db
from app.time_utils import legacy_utc_now


class EmailDelivery(db.Model):
    """
    Store the result of a payslip email delivery attempt.

    Every send or resend creates a new record. Historical records
    are never overwritten.
    """

    __tablename__ = "email_deliveries"

    STATUS_PENDING = "Pending"
    STATUS_DELIVERED = "Delivered"
    STATUS_FAILED = "Failed"

    VALID_STATUSES = {
        STATUS_PENDING,
        STATUS_DELIVERED,
        STATUS_FAILED,
    }

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

    payslip_id = db.Column(
        db.Integer,
        db.ForeignKey("payslips.id"),
        nullable=False,
        index=True,
    )

    payroll_period_id = db.Column(
        db.Integer,
        db.ForeignKey("payroll_periods.id"),
        nullable=False,
        index=True,
    )

    recipient_email = db.Column(
        db.String(255),
        nullable=False,
        default="",
        index=True,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default=STATUS_PENDING,
        index=True,
    )

    failure_reason = db.Column(
        db.Text,
        nullable=True,
    )

    sent_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    sent_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=legacy_utc_now,
        index=True,
    )

    employee = db.relationship(
        "Employee",
        backref=db.backref(
            "email_deliveries",
            lazy="dynamic",
            cascade="all, delete-orphan",
        ),
    )

    payslip = db.relationship(
        "Payslip",
        back_populates="email_deliveries",
    )

    payroll_period = db.relationship(
        "PayrollPeriod",
        backref=db.backref(
            "email_deliveries",
            lazy="dynamic",
            cascade="all, delete-orphan",
        ),
    )

    sender = db.relationship(
        "User",
        back_populates="sent_email_deliveries",
    )

    @property
    def is_delivered(self):
        """Return whether delivery succeeded."""

        return self.status == self.STATUS_DELIVERED

    @property
    def is_failed(self):
        """Return whether delivery failed."""

        return self.status == self.STATUS_FAILED

    @property
    def is_pending(self):
        """Return whether delivery is still pending."""

        return self.status == self.STATUS_PENDING

    @property
    def employee_name(self):
        """Return the employee's display name."""

        if not self.employee:
            return "Unknown Employee"

        first_name = self.employee.first_name or ""
        last_name = self.employee.last_name or ""
        full_name = f"{first_name} {last_name}".strip()

        return full_name or f"Employee #{self.employee_id}"

    @property
    def employee_number(self):
        """Return the associated employee number."""

        if not self.employee:
            return None

        return self.employee.employee_number

    @classmethod
    def create_pending(
        cls,
        *,
        employee_id,
        payslip_id,
        payroll_period_id,
        recipient_email,
        sent_by_id,
    ):
        """Create an unsaved pending delivery record."""

        normalised_email = str(
            recipient_email or ""
        ).strip().lower()

        return cls(
            employee_id=employee_id,
            payslip_id=payslip_id,
            payroll_period_id=payroll_period_id,
            recipient_email=normalised_email,
            status=cls.STATUS_PENDING,
            sent_by_id=sent_by_id,
        )

    def mark_delivered(self):
        """Mark the attempt as successfully delivered."""

        self.status = self.STATUS_DELIVERED
        self.failure_reason = None
        self.sent_at = legacy_utc_now()

    def mark_failed(self, reason):
        """Mark the attempt as failed."""

        self.status = self.STATUS_FAILED
        self.failure_reason = (
            str(reason).strip()
            or "Unknown email delivery failure."
        )
        self.sent_at = legacy_utc_now()

    def __repr__(self):
        return (
            f"<EmailDelivery id={self.id} "
            f"employee={self.employee_id} "
            f"status={self.status}>"
        )
