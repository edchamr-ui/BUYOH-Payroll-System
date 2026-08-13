from datetime import datetime

from app.extensions import db
from app.time_utils import legacy_utc_now


class Setting(db.Model):
    """Stores configurable system and payroll settings."""

    __tablename__ = "settings"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    setting_key = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    setting_value = db.Column(
        db.Text,
        nullable=False,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    updated_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=legacy_utc_now,
        onupdate=legacy_utc_now,
    )

    updater = db.relationship(
        "User",
        back_populates="updated_settings",
    )

    def __repr__(self):
        return f"<Setting {self.setting_key}>"
