"""Built-in South Africa statutory presets."""

from datetime import date, datetime
from decimal import Decimal

from app.models import StatutoryPreset


SOUTH_AFRICA_PRESETS = [
    {
        "preset_key": "ZA_ZAR_2027_ANNUAL",
        "country_code": "ZA",
        "country_name": "South Africa",
        "country_flag": "🇿🇦",
        "currency": "ZAR",
        "tax_year": 2027,
        "tax_period_label": "2027 tax year",
        "version": "1.0",
        "name": "South Africa ZAR Employees Tax 2027",
        "engine_type": StatutoryPreset.ENGINE_SOUTH_AFRICA,
        "effective_from": date(2026, 3, 1),
        "effective_to": date(2027, 2, 28),
        "verification_status": "Verified",
        "source_name": "SARS Guide for Employers 2027",
        "source_description": (
            "Official annual individual rates for 1 March 2026 to "
            "28 February 2027. Rebates, thresholds and medical credits "
            "require a dedicated South Africa engine."
        ),
        "source_reference": "SARS Employees Tax Guide 2027",
        "official_source_url": None,
        "last_verified_at": datetime(2026, 8, 2),
        "notes": "Annual bands are displayed for reference; import is blocked.",
        "paye_enabled": True,
        "employee_contribution_name": "UIF Employee",
        "employee_contribution_rate": Decimal("0.000000"),
        "employer_contribution_name": "UIF Employer / SDL",
        "employer_contribution_rate": Decimal("0.000000"),
        "contribution_ceiling": Decimal("0.00"),
        "levy_name": None,
        "levy_rate": Decimal("0.000000"),
        "supports_import": False,
        "supports_payroll": False,
        "is_published": True,
        "is_locked": True,
        "bands": [
            {"band_order": 1, "lower_limit": Decimal("0.00"), "upper_limit": Decimal("245100.00"), "rate": Decimal("0.180000")},
            {"band_order": 2, "lower_limit": Decimal("245100.00"), "upper_limit": Decimal("383100.00"), "rate": Decimal("0.260000")},
            {"band_order": 3, "lower_limit": Decimal("383100.00"), "upper_limit": Decimal("530200.00"), "rate": Decimal("0.310000")},
            {"band_order": 4, "lower_limit": Decimal("530200.00"), "upper_limit": Decimal("695800.00"), "rate": Decimal("0.360000")},
            {"band_order": 5, "lower_limit": Decimal("695800.00"), "upper_limit": Decimal("887000.00"), "rate": Decimal("0.390000")},
            {"band_order": 6, "lower_limit": Decimal("887000.00"), "upper_limit": Decimal("1878600.00"), "rate": Decimal("0.410000")},
            {"band_order": 7, "lower_limit": Decimal("1878600.00"), "upper_limit": None, "rate": Decimal("0.450000")},
        ],
    },
]
