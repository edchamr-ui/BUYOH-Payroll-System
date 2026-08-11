"""Tests for UK Statutory Sick Pay from 6 April 2026."""

from datetime import date
from decimal import Decimal

import pytest

from app.services.statutory_engines.uk_ssp import calculate_ssp_2026_27


def test_uses_flat_weekly_cap_for_higher_earner():
    result = calculate_ssp_2026_27(
        average_weekly_earnings="185",
        qualifying_days_per_week=5,
        qualifying_days_sick=3,
        sickness_start_date=date(2026, 4, 6),
    )

    assert result.weekly_rate == Decimal("123.25")
    assert result.amount == Decimal("73.95")
    assert result.weekly_cap_applied is True


def test_uses_80_percent_for_lower_earner():
    result = calculate_ssp_2026_27(
        average_weekly_earnings="145",
        qualifying_days_per_week=4,
        qualifying_days_sick=2,
    )

    assert result.weekly_rate == Decimal("116.00")
    assert result.amount == Decimal("58.00")
    assert result.weekly_cap_applied is False


def test_has_no_lower_earnings_limit():
    result = calculate_ssp_2026_27(
        average_weekly_earnings="50",
        qualifying_days_per_week=5,
        qualifying_days_sick=5,
    )

    assert result.weekly_rate == Decimal("40.00")
    assert result.amount == Decimal("40.00")


def test_pays_from_first_full_qualifying_day():
    result = calculate_ssp_2026_27(
        average_weekly_earnings="300",
        qualifying_days_per_week=5,
        qualifying_days_sick=1,
    )

    assert result.waiting_days_applied == 0
    assert result.payable_qualifying_days == 1
    assert result.amount == Decimal("24.65")


def test_uses_unrounded_daily_rate_before_rounding_total():
    result = calculate_ssp_2026_27(
        average_weekly_earnings="300",
        qualifying_days_per_week=6,
        qualifying_days_sick=4,
    )

    assert result.amount == Decimal("82.17")


def test_supports_full_week_for_every_valid_work_pattern():
    for qualifying_days in range(1, 8):
        result = calculate_ssp_2026_27(
            average_weekly_earnings="300",
            qualifying_days_per_week=qualifying_days,
            qualifying_days_sick=qualifying_days,
        )
        assert result.amount == Decimal("123.25")


def test_caps_entitlement_at_28_weeks_for_work_pattern():
    result = calculate_ssp_2026_27(
        average_weekly_earnings="300",
        qualifying_days_per_week=5,
        qualifying_days_sick=5,
        prior_paid_qualifying_days=138,
    )

    assert result.payable_qualifying_days == 2
    assert result.amount == Decimal("49.30")
    assert result.remaining_qualifying_days == 0


def test_returns_zero_after_entitlement_is_exhausted():
    result = calculate_ssp_2026_27(
        average_weekly_earnings="300",
        qualifying_days_per_week=5,
        qualifying_days_sick=3,
        prior_paid_qualifying_days=140,
    )

    assert result.payable_qualifying_days == 0
    assert result.amount == Decimal("0.00")


@pytest.mark.parametrize("qualifying_days", (0, 8, 2.5, True))
def test_rejects_invalid_weekly_work_patterns(qualifying_days):
    with pytest.raises(ValueError, match="Qualifying days per week"):
        calculate_ssp_2026_27(
            average_weekly_earnings="300",
            qualifying_days_per_week=qualifying_days,
            qualifying_days_sick=1,
        )


@pytest.mark.parametrize("earnings", ("-1", "NaN", "Infinity"))
def test_rejects_invalid_average_weekly_earnings(earnings):
    with pytest.raises(ValueError, match="Average weekly earnings"):
        calculate_ssp_2026_27(
            average_weekly_earnings=earnings,
            qualifying_days_per_week=5,
            qualifying_days_sick=1,
        )


def test_rejects_negative_sick_or_history_days():
    with pytest.raises(ValueError, match="Qualifying days sick"):
        calculate_ssp_2026_27(
            average_weekly_earnings="300",
            qualifying_days_per_week=5,
            qualifying_days_sick=-1,
        )

    with pytest.raises(ValueError, match="Prior paid qualifying days"):
        calculate_ssp_2026_27(
            average_weekly_earnings="300",
            qualifying_days_per_week=5,
            qualifying_days_sick=1,
            prior_paid_qualifying_days=-1,
        )


def test_rejects_pre_reform_absence_for_transitional_processing():
    with pytest.raises(ValueError, match="transitional SSP rules"):
        calculate_ssp_2026_27(
            average_weekly_earnings="300",
            qualifying_days_per_week=5,
            qualifying_days_sick=1,
            sickness_start_date=date(2026, 4, 5),
        )


def test_rejects_start_outside_2026_27_tax_year():
    with pytest.raises(ValueError, match="through 5 April 2027"):
        calculate_ssp_2026_27(
            average_weekly_earnings="300",
            qualifying_days_per_week=5,
            qualifying_days_sick=1,
            sickness_start_date=date(2027, 4, 6),
        )
