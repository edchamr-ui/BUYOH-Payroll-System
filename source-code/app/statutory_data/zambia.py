"""Built-in Zambia statutory presets."""

from datetime import date, datetime
from decimal import Decimal

from app.models import StatutoryPreset


ZAMBIA_PRESETS = [
    {
        "preset_key": "ZM_ZMW_2026_MONTHLY",
        "country_code": "ZM",
        "country_name": "Zambia",
        "country_flag": "🇿🇲",
        "currency": "ZMW",
        "tax_year": 2026,
        "tax_period_label": "2026",
        "version": "1.0",
        "name": "Zambia ZMW PAYE Rules 2026",
        "engine_type": StatutoryPreset.ENGINE_ZAMBIA,
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "verification_status": "Verified",
        "source_name": "Zambia Revenue Authority PAYE Calculator 2026",
        "source_description": "Official monthly PAYE bands published by ZRA.",
        "source_reference": "ZRA PAYE Calculator 2026",
        "official_source_url": None,
        "last_verified_at": datetime(2026, 8, 2),
        "notes": "Dedicated Zambia contribution handling is still required.",
        "paye_enabled": True,
        "employee_contribution_name": "NAPSA / statutory contribution",
        "employee_contribution_rate": Decimal("0.000000"),
        "employer_contribution_name": "NAPSA / statutory contribution",
        "employer_contribution_rate": Decimal("0.000000"),
        "contribution_ceiling": Decimal("0.00"),
        "levy_name": None,
        "levy_rate": Decimal("0.000000"),
        "supports_import": False,
        "supports_payroll": False,
        "is_published": True,
        "is_locked": True,
        "bands": [
            {"band_order": 1, "lower_limit": Decimal("0.00"), "upper_limit": Decimal("5100.00"), "rate": Decimal("0.000000")},
            {"band_order": 2, "lower_limit": Decimal("5100.00"), "upper_limit": Decimal("7100.00"), "rate": Decimal("0.200000")},
            {"band_order": 3, "lower_limit": Decimal("7100.00"), "upper_limit": Decimal("9200.00"), "rate": Decimal("0.300000")},
            {"band_order": 4, "lower_limit": Decimal("9200.00"), "upper_limit": None, "rate": Decimal("0.370000")},
        ],
    },
]
