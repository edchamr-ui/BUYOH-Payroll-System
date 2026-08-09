"""Regression tests for the Botswana resident monthly PAYE engine."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.statutory_engines.base import (
    InvalidStatutoryConfigurationError,
)
from app.services.statutory_engines.botswana import (
    BotswanaStatutoryEngine,
)


def band(order, lower, upper, rate):
    return SimpleNamespace(
        band_order=order,
        lower_limit=Decimal(lower),
        upper_limit=(Decimal(upper) if upper is not None else None),
        rate=Decimal(rate),
    )


@pytest.fixture
def resident_config():
    return SimpleNamespace(
        currency="BWP",
        paye_enabled=True,
        tax_bands=(
            band(1, "0", "4000", "0"),
            band(2, "4000", "7000", "0.05"),
            band(3, "7000", "10000", "0.125"),
            band(4, "10000", "13000", "0.1875"),
            band(5, "13000", "33333.33", "0.25"),
            band(6, "33333.33", None, "0.275"),
        ),
        nssa_employee_rate=Decimal("0"),
        nssa_employer_rate=Decimal("0"),
        nssa_monthly_ceiling=Decimal("0"),
        aids_levy_rate=Decimal("0"),
        tax_residency="Resident",
    )


@pytest.mark.parametrize(
    ("income", "expected_tax"),
    (
        ("4000", "0.00"),
        ("4001", "0.05"),
        ("7000", "150.00"),
        ("10000", "525.00"),
        ("13000", "1087.50"),
        ("18000", "2337.50"),
        # The progressive bands annualize to P408,000 and produce
        # P76,250 annually, or P6,354.17 monthly after rounding.
        ("34000", "6354.17"),
    ),
)
def test_resident_monthly_paye_boundaries(
    resident_config,
    income,
    expected_tax,
):
    result = BotswanaStatutoryEngine().calculate_paye(
        taxable_income=Decimal(income),
        statutory_config=resident_config,
    )

    assert result == Decimal(expected_tax)


def test_rejects_non_bwp_configuration(resident_config):
    resident_config.currency = "USD"

    with pytest.raises(InvalidStatutoryConfigurationError):
        BotswanaStatutoryEngine().calculate_paye(
            taxable_income=Decimal("18000"),
            statutory_config=resident_config,
        )


def test_rejects_unverified_band_set(resident_config):
    resident_config.tax_bands = resident_config.tax_bands[:-1]

    with pytest.raises(InvalidStatutoryConfigurationError):
        BotswanaStatutoryEngine().calculate_paye(
            taxable_income=Decimal("18000"),
            statutory_config=resident_config,
        )


@pytest.mark.parametrize(
    ("income", "expected_tax"),
    (
        ("7000", "350.00"),
        ("10000", "725.00"),
        ("13000", "1287.50"),
        # The official worked example contains a small arithmetic
        # inconsistency; the published progressive bands yield P21,679.18.
        ("89000", "21679.18"),
    ),
)
def test_non_resident_monthly_paye(
    resident_config,
    income,
    expected_tax,
):
    resident_config.tax_residency = "Non-Resident"

    result = BotswanaStatutoryEngine().calculate_paye(
        taxable_income=Decimal(income),
        statutory_config=resident_config,
    )

    assert result == Decimal(expected_tax)


def test_rejects_unknown_tax_residency(resident_config):
    resident_config.tax_residency = "Citizen"

    with pytest.raises(InvalidStatutoryConfigurationError):
        BotswanaStatutoryEngine().calculate_paye(
            taxable_income=Decimal("18000"),
            statutory_config=resident_config,
        )
