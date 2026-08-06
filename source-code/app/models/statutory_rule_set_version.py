"""Snapshot model for statutory rule-set update history."""

from datetime import datetime

from app.extensions import db


class StatutoryRuleSetVersion(db.Model):
    """
    Preserve an immutable snapshot before each statutory update.

    Historical payroll records are not recalculated. The snapshot
    exists for audit, review and future rollback support.
    """

    __tablename__ = "statutory_rule_set_versions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    rule_set_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "statutory_rule_sets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_preset_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "statutory_presets.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    source_preset_key = db.Column(
        db.String(120),
        nullable=True,
        index=True,
    )

    source_preset_version = db.Column(
        db.String(50),
        nullable=True,
        index=True,
    )

    snapshot_data = db.Column(
        db.JSON,
        nullable=False,
    )

    change_summary = db.Column(
        db.JSON,
        nullable=False,
        default=dict,
    )

    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    rule_set = db.relationship(
        "StatutoryRuleSet",
        foreign_keys=[rule_set_id],
        backref=db.backref(
            "version_history",
            lazy="select",
            cascade="all, delete-orphan",
            order_by="StatutoryRuleSetVersion.created_at.desc()",
        ),
    )

    source_preset = db.relationship(
        "StatutoryPreset",
        foreign_keys=[source_preset_id],
        lazy="select",
    )

    created_by_user = db.relationship(
        "User",
        foreign_keys=[created_by_user_id],
        lazy="select",
    )

    def __repr__(self):
        return (
            f"<StatutoryRuleSetVersion "
            f"rule_set_id={self.rule_set_id} "
            f"version={self.source_preset_version!r}>"
        )

