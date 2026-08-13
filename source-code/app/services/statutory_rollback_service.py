"""Transactional rollback service for statutory rule-set snapshots."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import StatutoryPreset, StatutoryRuleSetVersion, TaxBand
from app.services.audit_log_service import AuditLogService
from app.time_utils import legacy_utc_now


class StatutoryRollbackError(Exception):
    """Raised when a statutory rollback cannot be completed safely."""


class StatutoryRollbackService:
    """Restore one operational statutory rule from a preserved snapshot."""

    @staticmethod
    def _decimal(value, default="0"):
        if value is None:
            return Decimal(default)
        return Decimal(str(value))

    @staticmethod
    def _date(value):
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @classmethod
    def _snapshot_current_rule(cls, rule_set):
        return {
            "name": rule_set.name,
            "currency": rule_set.currency,
            "effective_from": rule_set.effective_from.isoformat() if rule_set.effective_from else None,
            "effective_to": rule_set.effective_to.isoformat() if rule_set.effective_to else None,
            "nssa_employee_rate": str(rule_set.nssa_employee_rate or 0),
            "nssa_employer_rate": str(rule_set.nssa_employer_rate or 0),
            "nssa_monthly_ceiling": str(rule_set.nssa_monthly_ceiling or 0),
            "aids_levy_rate": str(rule_set.aids_levy_rate or 0),
            "paye_enabled": bool(rule_set.paye_enabled),
            "is_active": bool(rule_set.is_active),
            "source_preset_id": rule_set.source_preset_id,
            "source_preset_key": rule_set.source_preset_key,
            "source_preset_version": rule_set.source_preset_version,
            "source_engine_type": rule_set.source_engine_type,
            "source_country_code": rule_set.source_country_code,
            "bands": [
                {
                    "band_order": band.band_order,
                    "lower_limit": str(band.lower_limit),
                    "upper_limit": None if band.upper_limit is None else str(band.upper_limit),
                    "rate": str(band.rate),
                }
                for band in sorted(rule_set.tax_bands, key=lambda item: item.band_order)
            ],
        }

    @staticmethod
    def _resolve_source_preset(snapshot_data):
        preset_id = snapshot_data.get("source_preset_id")
        if preset_id:
            preset = StatutoryPreset.query.get(preset_id)
            if preset is not None:
                return preset

        preset_key = snapshot_data.get("source_preset_key")
        if preset_key:
            return StatutoryPreset.query.filter_by(preset_key=preset_key).first()

        return None

    @classmethod
    def rollback(cls, *, rule_set, snapshot, rolled_back_by_user_id):
        if snapshot.rule_set_id != rule_set.id:
            raise StatutoryRollbackError(
                "The selected snapshot does not belong to this statutory rule set."
            )

        restore_data = dict(snapshot.snapshot_data or {})
        if not restore_data:
            raise StatutoryRollbackError(
                "The selected snapshot does not contain restorable statutory data."
            )

        current_snapshot = StatutoryRuleSetVersion(
            rule_set_id=rule_set.id,
            source_preset_id=rule_set.source_preset_id,
            source_preset_key=rule_set.source_preset_key,
            source_preset_version=rule_set.source_preset_version,
            snapshot_data=cls._snapshot_current_rule(rule_set),
            change_summary={
                "rollback": {
                    "restored_snapshot_id": snapshot.id,
                    "restored_version": snapshot.source_preset_version,
                }
            },
            created_by_user_id=rolled_back_by_user_id,
        )
        db.session.add(current_snapshot)

        try:
            db.session.flush()

            rule_set.name = restore_data.get("name", rule_set.name)
            rule_set.currency = restore_data.get("currency", rule_set.currency)
            rule_set.effective_from = cls._date(restore_data.get("effective_from"))
            rule_set.effective_to = cls._date(restore_data.get("effective_to"))
            rule_set.nssa_employee_rate = cls._decimal(restore_data.get("nssa_employee_rate"))
            rule_set.nssa_employer_rate = cls._decimal(restore_data.get("nssa_employer_rate"))
            rule_set.nssa_monthly_ceiling = cls._decimal(restore_data.get("nssa_monthly_ceiling"))
            rule_set.aids_levy_rate = cls._decimal(restore_data.get("aids_levy_rate"))
            rule_set.paye_enabled = bool(restore_data.get("paye_enabled", False))
            rule_set.is_active = bool(restore_data.get("is_active", rule_set.is_active))

            source_preset = cls._resolve_source_preset(restore_data)
            rule_set.source_preset_id = source_preset.id if source_preset else restore_data.get("source_preset_id")
            rule_set.source_preset_key = restore_data.get("source_preset_key")
            rule_set.source_preset_version = restore_data.get("source_preset_version")
            rule_set.source_engine_type = restore_data.get("source_engine_type")
            rule_set.source_country_code = restore_data.get("source_country_code")
            rule_set.imported_from_library = bool(rule_set.source_preset_key)
            rule_set.imported_at = legacy_utc_now()
            rule_set.imported_by_user_id = rolled_back_by_user_id

            for band in list(rule_set.tax_bands):
                db.session.delete(band)
            db.session.flush()

            for band_data in restore_data.get("bands", []):
                db.session.add(
                    TaxBand(
                        rule_set_id=rule_set.id,
                        band_order=int(band_data["band_order"]),
                        lower_limit=cls._decimal(band_data.get("lower_limit")),
                        upper_limit=(
                            None
                            if band_data.get("upper_limit") is None
                            else cls._decimal(band_data.get("upper_limit"))
                        ),
                        rate=cls._decimal(band_data.get("rate")),
                    )
                )

            AuditLogService.log(
                user_id=rolled_back_by_user_id,
                action="Statutory Rule Rolled Back",
                entity_type="StatutoryRuleSet",
                entity_id=rule_set.id,
                description=(
                    f"Rolled back {rule_set.display_name} to snapshot {snapshot.id}, "
                    f"version {snapshot.source_preset_version or 'Manual'}. "
                    f"Previous current state preserved as snapshot {current_snapshot.id}. "
                    "Historical payroll records and payslips were not changed."
                ),
                commit=False,
            )

            db.session.commit()

        except (KeyError, TypeError, ValueError, SQLAlchemyError) as error:
            db.session.rollback()
            raise StatutoryRollbackError(
                "The rollback failed and all changes were reverted."
            ) from error

        return current_snapshot
