from datetime import date
from decimal import Decimal

import pytest

from app.services.statutory_engines.uk_sncp import calculate_sncp_2026_27


def calc(**overrides):
    values = {
        "average_weekly_earnings": "500",
        "accrued_weeks": 12,
        "paid_days": 7,
    }
    values.update(overrides)
    return calculate_sncp_2026_27(**values)


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


def test_one_week_accrues_for_one_confirmed_care_week():
    result = calc(accrued_weeks=1)
    assert result.accrued_days == 7
    assert result.payable_days == 7
    assert result.remaining_accrued_days == 0


def test_maximum_twelve_weeks_can_be_paid():
    result = calc(paid_days=84)
    assert result.payable_days == 84
    assert result.remaining_accrued_days == 0
    assert result.amount == Decimal("2331.84")


def test_payment_is_capped_by_accrued_care_weeks():
    result = calc(accrued_weeks=3, paid_days=28)
    assert result.payable_days == 21
    assert result.amount == Decimal("582.96")


def test_prior_history_reduces_accrued_entitlement():
    result = calc(accrued_weeks=4, paid_days=14, prior_paid_days=21)
    assert result.payable_days == 7
    assert result.remaining_accrued_days == 0


def test_no_pay_remains_after_accrued_entitlement_is_used():
    result = calc(accrued_weeks=2, prior_paid_days=14)
    assert result.payable_days == 0
    assert result.amount == Decimal("0.00")


def test_part_week_payroll_alignment_uses_unrounded_daily_rate():
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


def test_zero_accrued_weeks_produces_no_pay():
    result = calc(accrued_weeks=0)
    assert result.accrued_days == 0
    assert result.amount == Decimal("0.00")


def test_more_than_twelve_accrued_weeks_is_rejected():
    with pytest.raises(ValueError, match="12 weeks"):
        calc(accrued_weeks=13)


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
        ("accrued_weeks", -1),
        ("accrued_weeks", 1.5),
        ("paid_days", -1),
        ("paid_days", 1.5),
        ("prior_paid_days", -1),
        ("prior_paid_days", True),
    ),
)
def test_rejects_invalid_integer_inputs(field, value):
    with pytest.raises(ValueError):
        calc(**{field: value})


def test_rejects_non_date_payment_date():
    with pytest.raises(ValueError, match="must be a date"):
        calc(payment_date="2026-04-05")
