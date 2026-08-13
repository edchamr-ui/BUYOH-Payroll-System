"""Safely link legacy operational rules to statutory library presets."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    StatutoryPreset,
    StatutoryRuleSet,
)
from app.services.audit_log_service import AuditLogService
from app.time_utils import legacy_utc_now


class StatutoryAdoptionError(Exception):
    """Raised when a legacy rule cannot be linked safely."""


@dataclass(frozen=True)
class StatutoryAdoptionComparison:
    """Comparison between a manual rule and a library preset."""

    rule_set: StatutoryRuleSet
    preset: StatutoryPreset
    compatible: bool
    differences: tuple[str, ...]


class StatutoryAdoptionService:
    """Validate and adopt historical manual rules into library lineage."""

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

    @classmethod
    def compare(
        cls,
        rule_set,
        preset,
    ):
        """Compare one operational rule against one library preset."""

        differences = []

        scalar_checks = (
            (
                "Currency",
                rule_set.currency,
                preset.currency,
            ),
            (
                "Effective from",
                rule_set.effective_from,
                preset.effective_from,
            ),
            (
                "Effective to",
                rule_set.effective_to,
                preset.effective_to,
            ),
            (
                "Employee contribution rate",
                cls._decimal(
                    rule_set.nssa_employee_rate
                ),
                cls._decimal(
                    preset.employee_contribution_rate
                ),
            ),
            (
                "Employer contribution rate",
                cls._decimal(
                    rule_set.nssa_employer_rate
                ),
                cls._decimal(
                    preset.employer_contribution_rate
                ),
            ),
            (
                "Contribution ceiling",
                cls._decimal(
                    rule_set.nssa_monthly_ceiling
                ),
                cls._decimal(
                    preset.contribution_ceiling
                ),
            ),
            (
                "Levy rate",
                cls._decimal(
                    rule_set.aids_levy_rate
                ),
                cls._decimal(
                    preset.levy_rate
                ),
            ),
            (
                "PAYE enabled",
                bool(rule_set.paye_enabled),
                bool(preset.paye_enabled),
            ),
        )

        for label, actual, expected in scalar_checks:
            if actual != expected:
                differences.append(
                    f"{label}: operational={actual}, "
                    f"library={expected}"
                )

        rule_bands = list(
            sorted(
                rule_set.tax_bands,
                key=lambda band: (
                    band.band_order,
                    band.lower_limit,
                ),
            )
        )

        preset_bands = list(
            sorted(
                preset.bands,
                key=lambda band: (
                    band.band_order,
                    band.lower_limit,
                ),
            )
        )

        if len(rule_bands) != len(preset_bands):
            differences.append(
                "Tax-band count: "
                f"operational={len(rule_bands)}, "
                f"library={len(preset_bands)}"
            )
        else:
            for rule_band, preset_band in zip(
                rule_bands,
                preset_bands,
                strict=True,
            ):
                comparisons = (
                    (
                        "order",
                        rule_band.band_order,
                        preset_band.band_order,
                    ),
                    (
                        "lower",
                        cls._decimal(
                            rule_band.lower_limit
                        ),
                        cls._decimal(
                            preset_band.lower_limit
                        ),
                    ),
                    (
                        "upper",
                        (
                            None
                            if rule_band.upper_limit is None
                            else cls._decimal(
                                rule_band.upper_limit
                            )
                        ),
                        (
                            None
                            if preset_band.upper_limit is None
                            else cls._decimal(
                                preset_band.upper_limit
                            )
                        ),
                    ),
                    (
                        "rate",
                        cls._decimal(
                            rule_band.rate
                        ),
                        cls._decimal(
                            preset_band.rate
                        ),
                    ),
                )

                for field_name, actual, expected in comparisons:
                    if actual != expected:
                        differences.append(
                            "Tax band "
                            f"{preset_band.band_order} {field_name}: "
                            f"operational={actual}, "
                            f"library={expected}"
                        )

        return StatutoryAdoptionComparison(
            rule_set=rule_set,
            preset=preset,
            compatible=not differences,
            differences=tuple(differences),
        )

    @classmethod
    def adopt(
        cls,
        *,
        rule_set,
        preset,
        adopted_by_user_id,
    ):
        """
        Link an exactly matching legacy rule to a library preset.

        No payroll rates or tax bands are modified.
        """

        if rule_set.imported_from_library:
            raise StatutoryAdoptionError(
                "This operational rule is already linked "
                "to a statutory library preset."
            )

        if not preset.can_import:
            raise StatutoryAdoptionError(
                f"{preset.display_name} is not eligible for "
                "operational installation."
            )

        comparison = cls.compare(
            rule_set,
            preset,
        )

        if not comparison.compatible:
            raise StatutoryAdoptionError(
                "The operational rule does not exactly match "
                "the selected library preset. Review the "
                "comparison before adopting it."
            )

        rule_set.source_preset_id = preset.id
        rule_set.source_preset_key = preset.preset_key
        rule_set.source_preset_version = preset.version
        rule_set.source_engine_type = preset.engine_type
        rule_set.source_country_code = preset.country_code
        rule_set.imported_from_library = True
        rule_set.imported_at = legacy_utc_now()
        rule_set.imported_by_user_id = adopted_by_user_id

        try:
            AuditLogService.log(
                user_id=adopted_by_user_id,
                action="Legacy Statutory Rule Adopted",
                entity_type="StatutoryRuleSet",
                entity_id=rule_set.id,
                description=(
                    f"Linked legacy operational rule "
                    f"{rule_set.display_name} to "
                    f"{preset.preset_key} version "
                    f"{preset.version}. No rates or tax "
                    "bands were changed."
                ),
                commit=False,
            )

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()

            raise StatutoryAdoptionError(
                "The legacy statutory rule could not be linked."
            ) from error

        return comparison
