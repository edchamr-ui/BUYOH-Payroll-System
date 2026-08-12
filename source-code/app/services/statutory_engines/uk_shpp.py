"""United Kingdom Statutory Shared Parental Pay for 2026/27."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal("0.00")
PENNY = Decimal("0.01")
SHPP_STANDARD_WEEKLY_RATE_2026_27 = Decimal("194.32")
SHPP_EARNINGS_PERCENTAGE = Decimal("0.90")
SHPP_LOWER_EARNINGS_LIMIT_2026_27 = Decimal("129.00")
SHPP_MAX_WEEKS = 37
SHPP_MAX_DAYS = SHPP_MAX_WEEKS * 7
SHPP_RATE_YEAR_START_2026_27 = date(2026, 4, 5)
SHPP_RATE_YEAR_END_2026_27 = date(2027, 4, 4)


def _decimal(value, field_name):
    try:
        result = Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be a finite number.")
    return result


def _money(value):
    return Decimal(value).quantize(PENNY, rounding=ROUND_HALF_UP)


def _days(value, field_name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return value


@dataclass(frozen=True)
class StatutorySharedParentalPayResult:
    rate_year: str
    average_weekly_earnings: Decimal
    lower_earnings_limit: Decimal
    eligible_by_earnings: bool
    weekly_rate: Decimal
    allocated_days: int
    paid_days_requested: int
    payable_days: int
    prior_paid_days: int
    remaining_allocated_days: int
    amount: Decimal
    standard_rate_cap_applied: bool


def calculate_shpp_2026_27(*, average_weekly_earnings, allocated_days,
                           paid_days, prior_paid_days=0, payment_date=None):
    """Calculate ShPP from an employer-confirmed transferred pay allocation."""
    awe = _decimal(average_weekly_earnings, "Average weekly earnings")
    if awe < ZERO:
        raise ValueError("Average weekly earnings cannot be negative.")
    allocated_days = _days(allocated_days, "Allocated days")
    paid_days = _days(paid_days, "Paid days")
    prior_paid_days = _days(prior_paid_days, "Prior paid days")
    if allocated_days > SHPP_MAX_DAYS:
        raise ValueError("Allocated days cannot exceed 259 days (37 weeks).")
    if payment_date is not None:
        if not isinstance(payment_date, date):
            raise ValueError("Payment date must be a date.")
        if not SHPP_RATE_YEAR_START_2026_27 <= payment_date <= SHPP_RATE_YEAR_END_2026_27:
            raise ValueError("The 2026/27 ShPP routine only supports payment dates from 5 April 2026 through 4 April 2027.")
    eligible = awe >= SHPP_LOWER_EARNINGS_LIMIT_2026_27
    ninety_percent = awe * SHPP_EARNINGS_PERCENTAGE
    rate = min(SHPP_STANDARD_WEEKLY_RATE_2026_27, ninety_percent)
    remaining = max(0, allocated_days - prior_paid_days)
    payable_days = min(paid_days, remaining) if eligible else 0
    amount = _money((rate / Decimal(7)) * payable_days)
    return StatutorySharedParentalPayResult(
        rate_year="2026/27", average_weekly_earnings=_money(awe),
        lower_earnings_limit=SHPP_LOWER_EARNINGS_LIMIT_2026_27,
        eligible_by_earnings=eligible, weekly_rate=_money(rate),
        allocated_days=allocated_days, paid_days_requested=paid_days,
        payable_days=payable_days, prior_paid_days=prior_paid_days,
        remaining_allocated_days=max(0, remaining - payable_days), amount=amount,
        standard_rate_cap_applied=(ninety_percent > SHPP_STANDARD_WEEKLY_RATE_2026_27),
    )
