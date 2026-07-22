from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class TaxBandConfiguration:
    """Calculator-ready representation of one PAYE tax band."""

    band_order: int
    lower_limit: Decimal
    upper_limit: Optional[Decimal]
    rate: Decimal


@dataclass(frozen=True)
class StatutoryConfiguration:
    """
    Calculator-ready statutory payroll configuration.

    Tax bands are supplied by the database-backed statutory
    rules service.
    """

    currency: str

    nssa_employee_rate: Decimal
    nssa_employer_rate: Decimal
    nssa_monthly_ceiling: Decimal

    aids_levy_rate: Decimal
    paye_enabled: bool

    tax_bands: tuple[TaxBandConfiguration, ...] = ()


USD_STATUTORY_CONFIG = StatutoryConfiguration(
    currency="USD",
    nssa_employee_rate=Decimal("0.045"),
    nssa_employer_rate=Decimal("0.045"),
    nssa_monthly_ceiling=Decimal("700.00"),
    aids_levy_rate=Decimal("0.03"),
    paye_enabled=False,
    tax_bands=(),
)
