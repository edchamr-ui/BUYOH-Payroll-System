from datetime import date
from decimal import Decimal

import pytest

from app.services.statutory_engines.uk_smp import calculate_smp_2026_27


def test_first_six_weeks_use_ninety_percent_without_cap():
    result = calculate_smp_2026_27(
        average_weekly_earnings="500",
        paid_days=42,
        payment_date=date(2026, 4, 5),
    )

    assert result.higher_weekly_rate == Decimal("450.00")
    assert result.higher_rate_days == 42
    assert result.standard_rate_days == 0
    assert result.amount == Decimal("2700.00")


def test_remaining_weeks_use_standard_cap():
    result = calculate_smp_2026_27(
        average_weekly_earnings="500",
        paid_days=7,
        prior_paid_days=42,
    )

    assert result.standard_weekly_rate == Decimal("194.32")
    assert result.standard_rate_cap_applied is True
    assert result.amount == Decimal("194.32")


def test_low_earner_uses_ninety_percent_for_remaining_weeks():
    result = calculate_smp_2026_27(
        average_weekly_earnings="150",
        paid_days=7,
        prior_paid_days=42,
    )

    assert result.standard_weekly_rate == Decimal("135.00")
    assert result.standard_rate_cap_applied is False
    assert result.amount == Decimal("135.00")


def test_period_can_cross_six_week_rate_boundary():
    result = calculate_smp_2026_27(
        average_weekly_earnings="500",
        paid_days=7,
        prior_paid_days=38,
    )

    assert result.higher_rate_days == 4
    assert result.standard_rate_days == 3
    assert result.amount == Decimal("340.42")


def test_part_week_uses_unrounded_daily_apportionment():
    result = calculate_smp_2026_27(
        average_weekly_earnings="500",
        paid_days=3,
        prior_paid_days=42,
    )

    assert result.amount == Decimal("83.28")


def test_entitlement_is_capped_at_thirty_nine_weeks():
    result = calculate_smp_2026_27(
        average_weekly_earnings="500",
        paid_days=10,
        prior_paid_days=270,
    )

    assert result.payable_days == 3
    assert result.remaining_paid_days == 0
    assert result.amount == Decimal("83.28")


def test_no_entitlement_remains_after_maximum():
    result = calculate_smp_2026_27(
        average_weekly_earnings="500",
        paid_days=7,
        prior_paid_days=273,
    )

    assert result.payable_days == 0
    assert result.amount == Decimal("0.00")


@pytest.mark.parametrize("awe", ("128.99", 0))
def test_earnings_below_lower_earnings_limit_are_ineligible(awe):
    result = calculate_smp_2026_27(
        average_weekly_earnings=awe,
        paid_days=7,
    )

    assert result.eligible_by_earnings is False
    assert result.payable_days == 0
    assert result.amount == Decimal("0.00")


def test_lower_earnings_limit_is_inclusive():
    result = calculate_smp_2026_27(
        average_weekly_earnings="129",
        paid_days=7,
    )

    assert result.eligible_by_earnings is True
    assert result.amount == Decimal("116.10")


@pytest.mark.parametrize(
    "payment_date",
    (date(2026, 4, 5), date(2027, 4, 4)),
)
def test_accepts_2026_27_rate_year_boundaries(payment_date):
    result = calculate_smp_2026_27(
        average_weekly_earnings="500",
        paid_days=1,
        payment_date=payment_date,
    )

    assert result.rate_year == "2026/27"


@pytest.mark.parametrize(
    "payment_date",
    (date(2026, 4, 4), date(2027, 4, 5)),
)
def test_rejects_payment_dates_outside_rate_year(payment_date):
    with pytest.raises(ValueError, match="5 April 2026"):
        calculate_smp_2026_27(
            average_weekly_earnings="500",
            paid_days=1,
            payment_date=payment_date,
        )


@pytest.mark.parametrize("awe", (-1, "NaN", "Infinity", object()))
def test_rejects_invalid_average_weekly_earnings(awe):
    with pytest.raises(ValueError):
        calculate_smp_2026_27(
            average_weekly_earnings=awe,
            paid_days=1,
        )


@pytest.mark.parametrize(
    "field,value",
    (("paid_days", -1), ("paid_days", 1.5), ("prior_paid_days", -1), ("prior_paid_days", True)),
)
def test_rejects_invalid_day_counts(field, value):
    kwargs = {
        "average_weekly_earnings": "500",
        "paid_days": 1,
        "prior_paid_days": 0,
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        calculate_smp_2026_27(**kwargs)


def test_rejects_non_date_payment_date():
    with pytest.raises(ValueError, match="must be a date"):
        calculate_smp_2026_27(
            average_weekly_earnings="500",
            paid_days=1,
            payment_date="2026-04-05",
        )
