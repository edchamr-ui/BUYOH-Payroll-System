"""Transactional statutory rule-set update service."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    StatutoryRuleSetVersion,
    TaxBand,
)
from app.services.audit_log_service import AuditLogService
from app.services.statutory_update_difference_service import (
    StatutoryUpdateDifferenceService,
)
from app.services.statutory_update_service import (
    StatutoryUpdateService,
)


class StatutoryUpdateApplyError(Exception):
    """Raised when a statutory update cannot be applied safely."""


class StatutoryTransactionalUpdateService:
    """Apply verified statutory updates inside one database transaction."""

    @staticmethod
    def _json_value(value):
        """Convert values into JSON-safe representations."""

        if isinstance(value, Decimal):
            return str(value)

        if hasattr(value, "isoformat"):
            return value.isoformat()

        return value

    @classmethod
    def _snapshot_rule_set(cls, rule_set):
        """Return a complete JSON-safe snapshot of the current rule."""

        return {
            "name": rule_set.name,
            "currency": rule_set.currency,
            "effective_from": cls._json_value(
                rule_set.effective_from
            ),
            "effective_to": cls._json_value(
                rule_set.effective_to
            ),
            "nssa_employee_rate": cls._json_value(
                rule_set.nssa_employee_rate
            ),
            "nssa_employer_rate": cls._json_value(
                rule_set.nssa_employer_rate
            ),
            "nssa_monthly_ceiling": cls._json_value(
                rule_set.nssa_monthly_ceiling
            ),
            "aids_levy_rate": cls._json_value(
                rule_set.aids_levy_rate
            ),
            "paye_enabled": bool(
                rule_set.paye_enabled
            ),
            "is_active": bool(
                rule_set.is_active
            ),
            "source_preset_id": rule_set.source_preset_id,
            "source_preset_key": rule_set.source_preset_key,
            "source_preset_version": (
                rule_set.source_preset_version
            ),
            "source_engine_type": (
                rule_set.source_engine_type
            ),
            "source_country_code": (
                rule_set.source_country_code
            ),
            "bands": [
                {
                    "band_order": band.band_order,
                    "lower_limit": cls._json_value(
                        band.lower_limit
                    ),
                    "upper_limit": cls._json_value(
                        band.upper_limit
                    ),
                    "rate": cls._json_value(
                        band.rate
                    ),
                }
                for band in sorted(
                    rule_set.tax_bands,
                    key=lambda item: item.band_order,
                )
            ],
        }

    @classmethod
    def _change_summary(cls, report):
        """Return a compact JSON-safe update summary."""

        return {
            "field_changes": [
                {
                    "field_name": item.field_name,
                    "current_value": cls._json_value(
                        item.current_value
                    ),
                    "new_value": cls._json_value(
                        item.new_value
                    ),
                }
                for item in report.field_differences
            ],
            "band_changes": [
                {
                    "band_order": item.band_order,
                    "change_type": item.change_type,
                    "current_lower": cls._json_value(
                        item.current_lower
                    ),
                    "current_upper": cls._json_value(
                        item.current_upper
                    ),
                    "current_rate": cls._json_value(
                        item.current_rate
                    ),
                    "new_lower": cls._json_value(
                        item.new_lower
                    ),
                    "new_upper": cls._json_value(
                        item.new_upper
                    ),
                    "new_rate": cls._json_value(
                        item.new_rate
                    ),
                }
                for item in report.band_differences
            ],
        }

    @classmethod
    def apply_update(
        cls,
        *,
        rule_set,
        applied_by_user_id,
    ):
        """
        Apply the newest compatible verified package transactionally.

        Existing payroll records and payslips are not modified.
        """

        item = StatutoryUpdateService.compare_rule_set(
            rule_set
        )

        if not item.update_available:
            raise StatutoryUpdateApplyError(
                "No newer compatible statutory package "
                "is available for this rule set."
            )

        latest_preset = item.latest_preset

        if latest_preset is None:
            raise StatutoryUpdateApplyError(
                "The latest statutory package could not be found."
            )

        if not latest_preset.can_import:
            raise StatutoryUpdateApplyError(
                f"{latest_preset.display_name} is not approved "
                "for payroll installation."
            )

        report = StatutoryUpdateDifferenceService.compare(
            rule_set,
            latest_preset,
        )

        snapshot = StatutoryRuleSetVersion(
            rule_set_id=rule_set.id,
            source_preset_id=rule_set.source_preset_id,
            source_preset_key=rule_set.source_preset_key,
            source_preset_version=(
                rule_set.source_preset_version
            ),
            snapshot_data=cls._snapshot_rule_set(
                rule_set
            ),
            change_summary=cls._change_summary(
                report
            ),
            created_by_user_id=applied_by_user_id,
        )

        db.session.add(snapshot)

        try:
            db.session.flush()

            rule_set.name = latest_preset.name
            rule_set.currency = latest_preset.currency
            rule_set.effective_from = (
                latest_preset.effective_from
            )
            rule_set.effective_to = (
                latest_preset.effective_to
            )
            rule_set.nssa_employee_rate = (
                latest_preset.employee_contribution_rate
            )
            rule_set.nssa_employer_rate = (
                latest_preset.employer_contribution_rate
            )
            rule_set.nssa_monthly_ceiling = (
                latest_preset.contribution_ceiling
            )
            rule_set.aids_levy_rate = (
                latest_preset.levy_rate
            )
            rule_set.paye_enabled = bool(
                latest_preset.paye_enabled
            )

            rule_set.source_preset_id = (
                latest_preset.id
            )
            rule_set.source_preset_key = (
                latest_preset.preset_key
            )
            rule_set.source_preset_version = (
                latest_preset.version
            )
            rule_set.source_engine_type = (
                latest_preset.engine_type
            )
            rule_set.source_country_code = (
                latest_preset.country_code
            )
            rule_set.imported_from_library = True
            rule_set.imported_at = datetime.utcnow()
            rule_set.imported_by_user_id = (
                applied_by_user_id
            )

            for band in list(rule_set.tax_bands):
                db.session.delete(band)

            db.session.flush()

            for preset_band in latest_preset.bands:
                db.session.add(
                    TaxBand(
                        rule_set_id=rule_set.id,
                        band_order=(
                            preset_band.band_order
                        ),
                        lower_limit=(
                            preset_band.lower_limit
                        ),
                        upper_limit=(
                            preset_band.upper_limit
                        ),
                        rate=preset_band.rate,
                    )
                )

            AuditLogService.log(
                user_id=applied_by_user_id,
                action="Statutory Package Updated",
                entity_type="StatutoryRuleSet",
                entity_id=rule_set.id,
                description=(
                    f"Updated {rule_set.display_name} from "
                    f"version {item.installed_version} to "
                    f"{item.latest_version}. Snapshot "
                    f"{snapshot.id} was preserved. Historical "
                    "payroll records were not changed."
                ),
                commit=False,
            )

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()

            raise StatutoryUpdateApplyError(
                "The statutory update failed and all changes "
                "were rolled back."
            ) from error

        return snapshot
