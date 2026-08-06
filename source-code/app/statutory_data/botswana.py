"""Built-in Botswana statutory presets."""

from datetime import date, datetime
from decimal import Decimal

from app.models import StatutoryPreset


BOTSWANA_PRESETS = [
    {
        "preset_key": "BW_BWP_2026_CATALOGUE",
        "country_code": "BW",
        "country_name": "Botswana",
        "country_flag": "🇧🇼",
        "currency": "BWP",
        "tax_year": 2026,
        "tax_period_label": "2026",
        "version": "catalogue-1.0",
        "name": "Botswana BWP PAYE Rules 2026",
        "engine_type": StatutoryPreset.ENGINE_BOTSWANA,
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "verification_status": "Source Located",
        "source_name": "Botswana Unified Revenue Service Tax Table 2026",
        "source_description": (
            "BURS publishes a 2026 tax table. Resident and non-resident "
            "calculation details must be encoded before import."
        ),
        "source_reference": "BURS Tax Table 2026",
        "official_source_url": None,
        "last_verified_at": datetime(2026, 8, 2),
        "notes": "Catalogue-only until the Botswana PAYE engine is implemented.",
        "paye_enabled": False,
        "employee_contribution_name": None,
        "employee_contribution_rate": Decimal("0.000000"),
        "employer_contribution_name": None,
        "employer_contribution_rate": Decimal("0.000000"),
        "contribution_ceiling": Decimal("0.00"),
        "levy_name": None,
        "levy_rate": Decimal("0.000000"),
        "supports_import": False,
        "supports_payroll": False,
        "is_published": True,
        "is_locked": True,
        "bands": [],
    },
]
