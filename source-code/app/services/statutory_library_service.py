"""Database-backed statutory preset library and import service."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import (
    StatutoryPreset,
    StatutoryPresetBand,
    StatutoryRuleSet,
    TaxBand,
)
from app.services.audit_log_service import AuditLogService
from app.statutory_data import BUILTIN_PRESETS
from app.time_utils import legacy_utc_now


class StatutoryLibraryError(Exception):
    """Base exception for statutory library operations."""


class StatutoryPresetNotFoundError(StatutoryLibraryError):
    """Raised when a requested preset does not exist."""


class StatutoryPresetAlreadyImportedError(StatutoryLibraryError):
    """Raised when the selected preset is already installed."""


class StatutoryPresetImportError(StatutoryLibraryError):
    """Raised when a statutory preset cannot be imported."""


class StatutoryPresetSeedError(StatutoryLibraryError):
    """Raised when built-in presets cannot be seeded."""


@dataclass(frozen=True)
class StatutoryImportResult:
    rule_set: StatutoryRuleSet
    imported_band_count: int
    preset: StatutoryPreset


class StatutoryLibraryService:
    """Provide, seed and import database-backed statutory presets."""

    @classmethod
    def list_presets(cls, *, published_only=True):
        query = StatutoryPreset.query

        if published_only:
            query = query.filter(
                StatutoryPreset.is_published.is_(True)
            )

        return (
            query.order_by(
                StatutoryPreset.country_name.asc(),
                StatutoryPreset.tax_year.desc(),
                StatutoryPreset.currency.asc(),
                StatutoryPreset.effective_from.desc(),
            ).all()
        )

    @classmethod
    def get_preset(cls, preset_key):
        key = str(preset_key or "").strip()

        preset = (
            StatutoryPreset.query
            .filter_by(
                preset_key=key,
                is_published=True,
            )
            .first()
        )

        if preset is None:
            raise StatutoryPresetNotFoundError(
                "The selected statutory preset does not exist "
                "or is not published."
            )

        return preset

    @staticmethod
    def _find_existing_rule_set(preset):
        return (
            StatutoryRuleSet.query
            .filter(
                db.or_(
                    StatutoryRuleSet.source_preset_id
                    == preset.id,
                    StatutoryRuleSet.source_preset_key
                    == preset.preset_key,
                )
            )
            .first()
        )

    @staticmethod
    def _find_overlapping_active_rule_set(preset):
        return (
            StatutoryRuleSet.query
            .filter(
                StatutoryRuleSet.currency == preset.currency,
                StatutoryRuleSet.is_active.is_(True),
                StatutoryRuleSet.effective_from
                <= preset.effective_to,
                db.or_(
                    StatutoryRuleSet.effective_to.is_(None),
                    StatutoryRuleSet.effective_to
                    >= preset.effective_from,
                ),
            )
            .first()
        )

    @staticmethod
    def _preset_to_operational_values(
        preset,
        imported_by_user_id,
    ):
        return {
            "name": preset.name,
            "currency": preset.currency,
            "effective_from": preset.effective_from,
            "effective_to": preset.effective_to,
            "nssa_employee_rate": (
                preset.employee_contribution_rate
            ),
            "nssa_employer_rate": (
                preset.employer_contribution_rate
            ),
            "nssa_monthly_ceiling": (
                preset.contribution_ceiling
            ),
            "aids_levy_rate": preset.levy_rate,
            "paye_enabled": preset.paye_enabled,
            "source_preset_id": preset.id,
            "source_preset_key": preset.preset_key,
            "source_preset_version": preset.version,
            "source_engine_type": preset.engine_type,
            "source_country_code": preset.country_code,
            "imported_from_library": True,
            "imported_at": legacy_utc_now(),
            "imported_by_user_id": imported_by_user_id,
        }

    @classmethod
    def import_preset(
        cls,
        *,
        preset_key,
        imported_by_user_id,
        activate=True,
    ):
        preset = cls.get_preset(preset_key)

        if not preset.can_import:
            raise StatutoryPresetImportError(
                f"{preset.display_name} cannot be imported yet. "
                f"Status: {preset.import_status}."
            )

        existing_rule_set = (
            cls._find_existing_rule_set(preset)
        )

        if existing_rule_set is not None:
            raise StatutoryPresetAlreadyImportedError(
                f"{preset.display_name} is already installed "
                f"as {existing_rule_set.display_name}."
            )

        should_activate = bool(activate)

        if (
            cls._find_overlapping_active_rule_set(preset)
            is not None
        ):
            should_activate = False

        rule_set = StatutoryRuleSet(
            **cls._preset_to_operational_values(
                preset,
                imported_by_user_id,
            ),
            is_active=should_activate,
        )

        db.session.add(rule_set)

        try:
            db.session.flush()

            for preset_band in preset.bands:
                db.session.add(
                    TaxBand(
                        rule_set_id=rule_set.id,
                        band_order=preset_band.band_order,
                        lower_limit=preset_band.lower_limit,
                        upper_limit=preset_band.upper_limit,
                        rate=preset_band.rate,
                    )
                )

            db.session.flush()

            AuditLogService.log(
                user_id=imported_by_user_id,
                action="Statutory Preset Imported",
                entity_type="StatutoryRuleSet",
                entity_id=rule_set.id,
                description=(
                    f"Imported {preset.display_name}; "
                    f"preset key {preset.preset_key}; "
                    f"version {preset.version}; "
                    f"engine {preset.engine_type}; "
                    f"{len(preset.bands)} PAYE tax band(s)."
                ),
                commit=False,
            )

            db.session.commit()

        except IntegrityError as error:
            db.session.rollback()
            raise StatutoryPresetImportError(
                "The statutory preset conflicts with existing data."
            ) from error

        except SQLAlchemyError as error:
            db.session.rollback()
            raise StatutoryPresetImportError(
                "The statutory preset could not be imported."
            ) from error

        return StatutoryImportResult(
            rule_set=rule_set,
            imported_band_count=len(preset.bands),
            preset=preset,
        )

    @classmethod
    def seed_builtin_presets(cls):
        seeded_count = 0
        updated_count = 0

        try:
            for raw_definition in BUILTIN_PRESETS:
                definition = deepcopy(raw_definition)
                bands = definition.pop("bands")

                existing = (
                    StatutoryPreset.query
                    .filter_by(
                        preset_key=definition["preset_key"]
                    )
                    .first()
                )

                if existing is None:
                    preset = StatutoryPreset(**definition)
                    db.session.add(preset)
                    db.session.flush()

                    for band_definition in bands:
                        db.session.add(
                            StatutoryPresetBand(
                                preset_id=preset.id,
                                **band_definition,
                            )
                        )

                    seeded_count += 1
                    continue

                for field_name, value in definition.items():
                    setattr(existing, field_name, value)

                existing.bands.clear()
                db.session.flush()

                for band_definition in bands:
                    db.session.add(
                        StatutoryPresetBand(
                            preset_id=existing.id,
                            **band_definition,
                        )
                    )

                updated_count += 1

            db.session.commit()

        except (IntegrityError, SQLAlchemyError) as error:
            db.session.rollback()
            raise StatutoryPresetSeedError(
                "The built-in statutory presets could not be seeded."
            ) from error

        return {
            "seeded": seeded_count,
            "updated": updated_count,
        }
