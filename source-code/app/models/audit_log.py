from datetime import datetime

from app.extensions import db


class AuditLog(db.Model):
    """Stores security and business activity performed by system users."""

    __tablename__ = "audit_logs"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    action = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    entity_type = db.Column(
        db.String(100),
        nullable=True,
    )

    entity_id = db.Column(
        db.Integer,
        nullable=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    ip_address = db.Column(
        db.String(45),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    user = db.relationship(
        "User",
        back_populates="audit_logs",
    )

    def __repr__(self):
        return f"<AuditLog {self.action}>"
