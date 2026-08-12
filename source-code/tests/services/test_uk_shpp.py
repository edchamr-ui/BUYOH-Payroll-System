from datetime import date
from decimal import Decimal
import pytest
from app.services.statutory_engines.uk_shpp import calculate_shpp_2026_27


def calc(**overrides):
    values = dict(average_weekly_earnings="500", allocated_days=259, paid_days=7)
    values.update(overrides)
    return calculate_shpp_2026_27(**values)


def test_standard_rate_cap():
    result = calc(payment_date=date(2026, 4, 5))
    assert result.weekly_rate == Decimal("194.32")
    assert result.amount == Decimal("194.32")


def test_low_earner_uses_ninety_percent():
    assert calc(average_weekly_earnings="150").amount == Decimal("135.00")


def test_partial_week_is_apportioned():
    assert calc(paid_days=3).amount == Decimal("83.28")


def test_prior_days_reduce_transferred_allocation():
    result = calc(allocated_days=21, paid_days=7, prior_paid_days=18)
    assert result.payable_days == 3
    assert result.remaining_allocated_days == 0


def test_no_pay_remains_after_allocation():
    assert calc(allocated_days=14, prior_paid_days=14).amount == Decimal("0.00")


def test_maximum_allocation_is_37_weeks():
    assert calc(allocated_days=259).allocated_days == 259


def test_allocation_above_37_weeks_is_rejected():
    with pytest.raises(ValueError, match="259"):
        calc(allocated_days=260)


@pytest.mark.parametrize("awe", ("128.99", 0))
def test_below_lower_earnings_limit_is_ineligible(awe):
    assert calc(average_weekly_earnings=awe).amount == Decimal("0.00")


def test_lower_earnings_limit_is_inclusive():
    assert calc(average_weekly_earnings="129").amount == Decimal("116.10")


@pytest.mark.parametrize("payment_date", (date(2026,4,5), date(2027,4,4)))
def test_rate_year_boundaries(payment_date):
    assert calc(payment_date=payment_date).rate_year == "2026/27"


@pytest.mark.parametrize("payment_date", (date(2026,4,4), date(2027,4,5)))
def test_dates_outside_rate_year_are_rejected(payment_date):
    with pytest.raises(ValueError, match="5 April 2026"):
        calc(payment_date=payment_date)


@pytest.mark.parametrize("awe", (-1, "NaN", "Infinity", object()))
def test_invalid_earnings_are_rejected(awe):
    with pytest.raises(ValueError):
        calc(average_weekly_earnings=awe)


@pytest.mark.parametrize("field,value", (("allocated_days",-1),("paid_days",-1),("paid_days",1.5),("prior_paid_days",True)))
def test_invalid_day_values_are_rejected(field, value):
    with pytest.raises(ValueError):
        calc(**{field:value})


def test_non_date_payment_date_is_rejected():
    with pytest.raises(ValueError, match="must be a date"):
        calc(payment_date="2026-04-05")
