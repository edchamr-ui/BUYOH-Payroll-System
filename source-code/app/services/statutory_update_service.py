"""Statutory update discovery and comparison service."""

from dataclasses import dataclass
from typing import Optional

from app.models import (
    StatutoryPreset,
    StatutoryRuleSet,
)


@dataclass(frozen=True)
class StatutoryUpdateItem:
    """One installed rule-set update comparison."""

    rule_set: StatutoryRuleSet
    installed_preset: Optional[StatutoryPreset]
    latest_preset: Optional[StatutoryPreset]
    installed_version: Optional[str]
    latest_version: Optional[str]
    update_available: bool
    status: str


class StatutoryUpdateService:
    """Compare installed operational rules with library presets."""

    @staticmethod
    def _version_key(value):
        """Return a stable comparison key for dotted versions."""

        raw = str(value or "").strip()

        if not raw:
            return tuple()

        parts = []

        for component in raw.replace("-", ".").split("."):
            cleaned = component.strip()

            if cleaned.isdigit():
                parts.append((0, int(cleaned)))
            else:
                parts.append((1, cleaned.lower()))

        return tuple(parts)

    @staticmethod
    def _installed_preset(rule_set):
        """Return the preset originally linked to the rule set."""

        if rule_set.source_preset_id:
            preset = StatutoryPreset.query.get(
                rule_set.source_preset_id
            )

            if preset is not None:
                return preset

        if rule_set.source_preset_key:
            return (
                StatutoryPreset.query
                .filter_by(
                    preset_key=rule_set.source_preset_key
                )
                .first()
            )

        return None

    @classmethod
    def _latest_compatible_preset(
        cls,
        rule_set,
        installed_preset=None,
    ):
        """
        Return the latest published preset for the same statutory period.

        A later tax year is a separate package, not an update.
        """

        if not rule_set.imported_from_library:
            return None

        if installed_preset is None:
            installed_preset = cls._installed_preset(
                rule_set
            )

        if installed_preset is None:
            return None

        presets = (
            StatutoryPreset.query
            .filter(
                StatutoryPreset.is_published.is_(True),
                StatutoryPreset.country_code
                == rule_set.source_country_code,
                StatutoryPreset.currency
                == rule_set.currency,
                StatutoryPreset.engine_type
                == rule_set.source_engine_type,
                StatutoryPreset.tax_year
                == installed_preset.tax_year,
                StatutoryPreset.effective_from
                == installed_preset.effective_from,
                StatutoryPreset.effective_to
                == installed_preset.effective_to,
            )
            .all()
        )

        if not presets:
            return None

        return max(
            presets,
            key=lambda preset: (
                cls._version_key(preset.version),
                preset.id,
            ),
        )

    @classmethod
    def compare_rule_set(cls, rule_set):
        """Return update information for one operational rule set."""

        if not rule_set.imported_from_library:
            return StatutoryUpdateItem(
                rule_set=rule_set,
                installed_preset=None,
                latest_preset=None,
                installed_version=None,
                latest_version=None,
                update_available=False,
                status="Manual Rule",
            )

        installed_preset = cls._installed_preset(
            rule_set
        )

        latest_preset = cls._latest_compatible_preset(
            rule_set,
            installed_preset=installed_preset,
        )

        installed_version = (
            str(rule_set.source_preset_version or "").strip()
            or None
        )

        latest_version = (
            str(
                latest_preset.version
                if latest_preset is not None
                else ""
            ).strip()
            or None
        )

        update_available = bool(
            latest_preset is not None
            and installed_version is not None
            and latest_version is not None
            and cls._version_key(latest_version)
            > cls._version_key(installed_version)
        )

        if update_available:
            status = "Update Available"
        elif latest_preset is None:
            status = "Library Record Missing"
        else:
            status = "Up to Date"

        return StatutoryUpdateItem(
            rule_set=rule_set,
            installed_preset=installed_preset,
            latest_preset=latest_preset,
            installed_version=installed_version,
            latest_version=latest_version,
            update_available=update_available,
            status=status,
        )

    @classmethod
    def list_updates(cls):
        """Return update comparisons for all operational rule sets."""

        rule_sets = (
            StatutoryRuleSet.query
            .order_by(
                StatutoryRuleSet.imported_from_library.desc(),
                StatutoryRuleSet.currency.asc(),
                StatutoryRuleSet.effective_from.desc(),
                StatutoryRuleSet.id.desc(),
            )
            .all()
        )

        return [
            cls.compare_rule_set(rule_set)
            for rule_set in rule_sets
        ]

    @classmethod
    def summary(cls):
        """Return update-centre summary counts."""

        items = cls.list_updates()

        return {
            "items": items,
            "installed_count": sum(
                1
                for item in items
                if item.rule_set.imported_from_library
            ),
            "update_count": sum(
                1
                for item in items
                if item.update_available
            ),
            "current_count": sum(
                1
                for item in items
                if item.status == "Up to Date"
            ),
            "manual_count": sum(
                1
                for item in items
                if item.status == "Manual Rule"
            ),
        }
