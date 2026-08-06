"""Built-in Kenya statutory presets."""

from datetime import date, datetime
from decimal import Decimal

from app.models import StatutoryPreset


KENYA_PRESETS = [
    {
        "preset_key": "KE_KES_2026_CURRENT",
        "country_code": "KE",
        "country_name": "Kenya",
        "country_flag": "🇰🇪",
        "currency": "KES",
        "tax_year": 2026,
        "tax_period_label": "Current rules in 2026",
        "version": "1.0",
        "name": "Kenya KES PAYE Rules 2026",
        "engine_type": StatutoryPreset.ENGINE_KENYA,
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "verification_status": "Verified",
        "source_name": "Kenya Revenue Authority PAYE",
        "source_description": (
            "Official monthly PAYE bands currently published by KRA. "
            "Personal relief and other deductions require a Kenya engine."
        ),
        "source_reference": "KRA PAYE Individual Tax Rates",
        "official_source_url": None,
        "last_verified_at": datetime(2026, 8, 2),
        "notes": "Monthly personal relief of KES 2,400 is not yet modelled.",
        "paye_enabled": True,
        "employee_contribution_name": "Affordable Housing Levy / SHIF",
        "employee_contribution_rate": Decimal("0.000000"),
        "employer_contribution_name": "Affordable Housing Levy",
        "employer_contribution_rate": Decimal("0.000000"),
        "contribution_ceiling": Decimal("0.00"),
        "levy_name": None,
        "levy_rate": Decimal("0.000000"),
        "supports_import": False,
        "supports_payroll": False,
        "is_published": True,
        "is_locked": True,
        "bands": [
            {"band_order": 1, "lower_limit": Decimal("0.00"), "upper_limit": Decimal("24000.00"), "rate": Decimal("0.100000")},
            {"band_order": 2, "lower_limit": Decimal("24000.00"), "upper_limit": Decimal("32333.00"), "rate": Decimal("0.250000")},
            {"band_order": 3, "lower_limit": Decimal("32333.00"), "upper_limit": Decimal("500000.00"), "rate": Decimal("0.300000")},
            {"band_order": 4, "lower_limit": Decimal("500000.00"), "upper_limit": Decimal("800000.00"), "rate": Decimal("0.325000")},
            {"band_order": 5, "lower_limit": Decimal("800000.00"), "upper_limit": None, "rate": Decimal("0.350000")},
        ],
    },
]
