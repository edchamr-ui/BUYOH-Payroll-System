from datetime import date
from decimal import Decimal

import pytest

from app.services.statutory_engines.uk_spbp import calculate_spbp_2026_27


def calc(**overrides):
    values = {
        "average_weekly_earnings": "500",
        "paid_days": 7,
    }
    values.update(overrides)
    return calculate_spbp_2026_27(**values)


def test_high_earner_uses_standard_weekly_cap():
    result = calc(payment_date=date(2026, 4, 5))
    assert result.weekly_rate == Decimal("194.32")
    assert result.standard_rate_cap_applied is True
    assert result.amount == Decimal("194.32")


def test_lower_earner_uses_ninety_percent_of_awe():
    result = calc(average_weekly_earnings="150")
    assert result.weekly_rate == Decimal("135.00")
    assert result.standard_rate_cap_applied is False
    assert result.amount == Decimal("135.00")


def test_two_complete_weeks_can_be_paid():
    result = calc(paid_days=14)
    assert result.payable_days == 14
    assert result.remaining_paid_days == 0
    assert result.amount == Decimal("388.64")


def test_second_separate_week_uses_prior_entitlement_history():
    result = calc(prior_paid_days=7)
    assert result.payable_days == 7
    assert result.remaining_paid_days == 0
    assert result.amount == Decimal("194.32")


def test_allocation_is_capped_at_two_weeks():
    result = calc(paid_days=7, prior_paid_days=10)
    assert result.payable_days == 4
    assert result.amount == Decimal("111.04")


def test_no_entitlement_remains_after_fourteen_days():
    result = calc(prior_paid_days=14)
    assert result.payable_days == 0
    assert result.remaining_paid_days == 0
    assert result.amount == Decimal("0.00")


def test_partial_week_uses_unrounded_daily_apportionment():
    assert calc(paid_days=3).amount == Decimal("83.28")


@pytest.mark.parametrize("awe", ("128.99", 0))
def test_earnings_below_lower_earnings_limit_are_ineligible(awe):
    result = calc(average_weekly_earnings=awe)
    assert result.eligible_by_earnings is False
    assert result.payable_days == 0
    assert result.amount == Decimal("0.00")


def test_lower_earnings_limit_is_inclusive():
    result = calc(average_weekly_earnings="129")
    assert result.eligible_by_earnings is True
    assert result.amount == Decimal("116.10")


@pytest.mark.parametrize("payment_date", (date(2026, 4, 5), date(2027, 4, 4)))
def test_accepts_rate_year_boundaries(payment_date):
    assert calc(payment_date=payment_date).rate_year == "2026/27"


@pytest.mark.parametrize("payment_date", (date(2026, 4, 4), date(2027, 4, 5)))
def test_rejects_dates_outside_rate_year(payment_date):
    with pytest.raises(ValueError, match="5 April 2026"):
        calc(payment_date=payment_date)


@pytest.mark.parametrize("awe", (-1, "NaN", "Infinity", object()))
def test_rejects_invalid_average_weekly_earnings(awe):
    with pytest.raises(ValueError):
        calc(average_weekly_earnings=awe)


@pytest.mark.parametrize(
    "field,value",
    (
        ("paid_days", -1),
        ("paid_days", 1.5),
        ("prior_paid_days", -1),
        ("prior_paid_days", True),
    ),
)
def test_rejects_invalid_day_counts(field, value):
    with pytest.raises(ValueError):
        calc(**{field: value})


def test_rejects_non_date_payment_date():
    with pytest.raises(ValueError, match="must be a date"):
        calc(payment_date="2026-04-05")
