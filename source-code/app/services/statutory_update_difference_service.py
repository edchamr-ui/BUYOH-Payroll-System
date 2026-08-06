"""Build a side-by-side statutory update difference report."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class StatutoryFieldDifference:
    """One changed statutory field."""

    field_name: str
    current_value: Any
    new_value: Any


@dataclass(frozen=True)
class StatutoryBandDifference:
    """One changed, added or removed PAYE band."""

    band_order: int
    change_type: str
    current_lower: Any
    current_upper: Any
    current_rate: Any
    new_lower: Any
    new_upper: Any
    new_rate: Any


@dataclass(frozen=True)
class StatutoryDifferenceReport:
    """Complete comparison between an installed rule and a preset."""

    field_differences: tuple[StatutoryFieldDifference, ...]
    band_differences: tuple[StatutoryBandDifference, ...]

    @property
    def has_changes(self):
        return bool(
            self.field_differences
            or self.band_differences
        )


class StatutoryUpdateDifferenceService:
    """Compare current operational values with a newer preset."""

    @staticmethod
    def _decimal(value):
        if value is None:
            return None

        return Decimal(str(value))

    @classmethod
    def compare(cls, rule_set, preset):
        field_differences = []

        scalar_fields = (
            (
                "Employee contribution rate",
                cls._decimal(rule_set.nssa_employee_rate),
                cls._decimal(
                    preset.employee_contribution_rate
                ),
            ),
            (
                "Employer contribution rate",
                cls._decimal(rule_set.nssa_employer_rate),
                cls._decimal(
                    preset.employer_contribution_rate
                ),
            ),
            (
                "Contribution ceiling",
                cls._decimal(rule_set.nssa_monthly_ceiling),
                cls._decimal(preset.contribution_ceiling),
            ),
            (
                "Levy rate",
                cls._decimal(rule_set.aids_levy_rate),
                cls._decimal(preset.levy_rate),
            ),
            (
                "PAYE enabled",
                bool(rule_set.paye_enabled),
                bool(preset.paye_enabled),
            ),
        )

        for field_name, current_value, new_value in scalar_fields:
            if current_value != new_value:
                field_differences.append(
                    StatutoryFieldDifference(
                        field_name=field_name,
                        current_value=current_value,
                        new_value=new_value,
                    )
                )

        current_bands = {
            band.band_order: band
            for band in rule_set.tax_bands
        }

        new_bands = {
            band.band_order: band
            for band in preset.bands
        }

        band_differences = []

        for band_order in sorted(
            set(current_bands) | set(new_bands)
        ):
            current_band = current_bands.get(
                band_order
            )
            new_band = new_bands.get(
                band_order
            )

            if current_band is None:
                band_differences.append(
                    StatutoryBandDifference(
                        band_order=band_order,
                        change_type="Added",
                        current_lower=None,
                        current_upper=None,
                        current_rate=None,
                        new_lower=cls._decimal(
                            new_band.lower_limit
                        ),
                        new_upper=cls._decimal(
                            new_band.upper_limit
                        ),
                        new_rate=cls._decimal(
                            new_band.rate
                        ),
                    )
                )
                continue

            if new_band is None:
                band_differences.append(
                    StatutoryBandDifference(
                        band_order=band_order,
                        change_type="Removed",
                        current_lower=cls._decimal(
                            current_band.lower_limit
                        ),
                        current_upper=cls._decimal(
                            current_band.upper_limit
                        ),
                        current_rate=cls._decimal(
                            current_band.rate
                        ),
                        new_lower=None,
                        new_upper=None,
                        new_rate=None,
                    )
                )
                continue

            current_values = (
                cls._decimal(current_band.lower_limit),
                cls._decimal(current_band.upper_limit),
                cls._decimal(current_band.rate),
            )

            new_values = (
                cls._decimal(new_band.lower_limit),
                cls._decimal(new_band.upper_limit),
                cls._decimal(new_band.rate),
            )

            if current_values != new_values:
                band_differences.append(
                    StatutoryBandDifference(
                        band_order=band_order,
                        change_type="Changed",
                        current_lower=current_values[0],
                        current_upper=current_values[1],
                        current_rate=current_values[2],
                        new_lower=new_values[0],
                        new_upper=new_values[1],
                        new_rate=new_values[2],
                    )
                )

        return StatutoryDifferenceReport(
            field_differences=tuple(
                field_differences
            ),
            band_differences=tuple(
                band_differences
            ),
        )
