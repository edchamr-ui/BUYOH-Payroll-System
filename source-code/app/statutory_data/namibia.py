"""Built-in Namibia statutory presets."""

from datetime import date, datetime
from decimal import Decimal

from app.models import StatutoryPreset


NAMIBIA_PRESETS = [
    {
        "preset_key": "NA_NAD_2026_CATALOGUE",
        "country_code": "NA",
        "country_name": "Namibia",
        "country_flag": "🇳🇦",
        "currency": "NAD",
        "tax_year": 2026,
        "tax_period_label": "2026",
        "version": "catalogue-1.0",
        "name": "Namibia NAD Individual Tax Rules 2026",
        "engine_type": StatutoryPreset.ENGINE_NAMIBIA,
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "verification_status": "Source Located",
        "source_name": "Namibia Revenue Agency Individual Income Tax",
        "source_description": (
            "NamRA publishes progressive annual individual rates. "
            "Annualisation and payroll-period conversion are required."
        ),
        "source_reference": "NamRA Individual Income Tax Rates",
        "official_source_url": None,
        "last_verified_at": datetime(2026, 8, 2),
        "notes": "Catalogue-only until annualisation logic is implemented.",
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
