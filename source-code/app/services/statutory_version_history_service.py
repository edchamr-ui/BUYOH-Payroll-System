"""Read-only statutory rule-set version history service."""

from dataclasses import dataclass
from typing import Any

from app.models import (
    StatutoryRuleSet,
    StatutoryRuleSetVersion,
)


@dataclass(frozen=True)
class StatutoryVersionHistoryItem:
    """Presentation model for one statutory snapshot."""

    snapshot: StatutoryRuleSetVersion
    installed_version: str | None
    field_change_count: int
    band_change_count: int
    created_by_name: str
    snapshot_band_count: int
    source_preset_key: str | None
    snapshot_data: dict[str, Any]
    change_summary: dict[str, Any]


class StatutoryVersionHistoryService:
    """Provide version-history data for one operational rule set."""

    @staticmethod
    def _display_user(snapshot):
        user = snapshot.created_by_user

        if user is None:
            return "Unknown user"

        if hasattr(user, "full_name") and user.full_name:
            return user.full_name

        if hasattr(user, "username") and user.username:
            return user.username

        return f"User #{user.id}"

    @classmethod
    def list_for_rule_set(
        cls,
        rule_set: StatutoryRuleSet,
    ):
        snapshots = (
            StatutoryRuleSetVersion.query
            .filter_by(rule_set_id=rule_set.id)
            .order_by(
                StatutoryRuleSetVersion.created_at.desc(),
                StatutoryRuleSetVersion.id.desc(),
            )
            .all()
        )

        items = []

        for snapshot in snapshots:
            snapshot_data = dict(
                snapshot.snapshot_data or {}
            )
            change_summary = dict(
                snapshot.change_summary or {}
            )

            field_changes = list(
                change_summary.get(
                    "field_changes",
                    [],
                )
            )
            band_changes = list(
                change_summary.get(
                    "band_changes",
                    [],
                )
            )
            bands = list(
                snapshot_data.get(
                    "bands",
                    [],
                )
            )

            items.append(
                StatutoryVersionHistoryItem(
                    snapshot=snapshot,
                    installed_version=(
                        snapshot.source_preset_version
                    ),
                    field_change_count=len(
                        field_changes
                    ),
                    band_change_count=len(
                        band_changes
                    ),
                    created_by_name=cls._display_user(
                        snapshot
                    ),
                    snapshot_band_count=len(bands),
                    source_preset_key=(
                        snapshot.source_preset_key
                    ),
                    snapshot_data=snapshot_data,
                    change_summary=change_summary,
                )
            )

        return items

    @classmethod
    def summary_for_rule_set(
        cls,
        rule_set: StatutoryRuleSet,
    ):
        items = cls.list_for_rule_set(
            rule_set
        )

        return {
            "rule_set": rule_set,
            "items": items,
            "snapshot_count": len(items),
            "latest_snapshot": (
                items[0]
                if items
                else None
            ),
            "current_version": (
                rule_set.source_preset_version
                if rule_set.imported_from_library
                else None
            ),
        }
