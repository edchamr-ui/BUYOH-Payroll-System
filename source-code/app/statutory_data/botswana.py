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
        "tax_period_label": "2026/27 (Resident Monthly)",
        "version": "2026.07-resident-1.0",
        "name": "Botswana BWP Resident PAYE Rules 2026/27",
        "engine_type": StatutoryPreset.ENGINE_BOTSWANA,
        "effective_from": date(2026, 7, 1),
        "effective_to": date(2027, 6, 30),
        "verification_status": "Verified",
        "source_name": "Botswana Unified Revenue Service Tax Table 2026",
        "source_description": (
            "Official resident monthly PAYE bands effective from July "
            "2026. Non-resident employees require a separate rule path."
        ),
        "source_reference": (
            "BURS Tax Table and Guidance Notes 2026, Part II, Table I, "
            "page 158; worked examples on page 159"
        ),
        "official_source_url": None,
        "last_verified_at": datetime(2026, 8, 2),
        "notes": (
            "Verified for resident employees paid monthly. The bands are "
            "the official annual resident bands divided by 12. Do not use "
            "this preset for non-resident employees."
        ),
        "paye_enabled": True,
        "employee_contribution_name": None,
        "employee_contribution_rate": Decimal("0.000000"),
        "employer_contribution_name": None,
        "employer_contribution_rate": Decimal("0.000000"),
        "contribution_ceiling": Decimal("0.00"),
        "levy_name": None,
        "levy_rate": Decimal("0.000000"),
        "supports_import": True,
        "supports_payroll": True,
        "is_published": True,
        "is_locked": True,
        "bands": [
            {
                "band_order": 1,
                "lower_limit": Decimal("0.00"),
                "upper_limit": Decimal("4000.00"),
                "rate": Decimal("0.000000"),
            },
            {
                "band_order": 2,
                "lower_limit": Decimal("4000.00"),
                "upper_limit": Decimal("7000.00"),
                "rate": Decimal("0.050000"),
            },
            {
                "band_order": 3,
                "lower_limit": Decimal("7000.00"),
                "upper_limit": Decimal("10000.00"),
                "rate": Decimal("0.125000"),
            },
            {
                "band_order": 4,
                "lower_limit": Decimal("10000.00"),
                "upper_limit": Decimal("13000.00"),
                "rate": Decimal("0.187500"),
            },
            {
                "band_order": 5,
                "lower_limit": Decimal("13000.00"),
                "upper_limit": Decimal("33333.33"),
                "rate": Decimal("0.250000"),
            },
            {
                "band_order": 6,
                "lower_limit": Decimal("33333.33"),
                "upper_limit": None,
                "rate": Decimal("0.275000"),
            },
        ],
    },
]
