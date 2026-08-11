"""United Kingdom Statutory Sick Pay for tax year 2026/27.

This module implements the post-6-April-2026 calculation core.  Absences
which straddle 6 April 2026 require the separate HMRC transitional rules and
are deliberately rejected by the dated public function.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0.00")
PENNY = Decimal("0.01")
SSP_WEEKLY_CAP_2026_27 = Decimal("123.25")
SSP_EARNINGS_PERCENTAGE_2026_27 = Decimal("0.80")
SSP_MAX_WEEKS = 28
TAX_YEAR_START_2026_27 = date(2026, 4, 6)
TAX_YEAR_END_2026_27 = date(2027, 4, 5)


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


@dataclass(frozen=True)
class StatutorySickPayResult:
    """Auditable SSP result for one payroll calculation."""

    tax_year: str
    average_weekly_earnings: Decimal
    weekly_rate: Decimal
    qualifying_days_per_week: int
    qualifying_days_sick: int
    payable_qualifying_days: int
    prior_paid_qualifying_days: int
    remaining_qualifying_days: int
    daily_rate_unrounded: Decimal
    amount: Decimal
    weekly_cap_applied: bool
    waiting_days_applied: int


def calculate_ssp_2026_27(
    *,
    average_weekly_earnings,
    qualifying_days_per_week,
    qualifying_days_sick,
    prior_paid_qualifying_days=0,
    sickness_start_date=None,
):
    """Calculate SSP under the rules applying from 6 April 2026.

    ``qualifying_days_sick`` is the count of full qualifying workdays in the
    payroll period, not calendar days.  The caller remains responsible for
    eligibility checks unrelated to earnings and for identifying linked
    periods of incapacity.  Pass their cumulative paid qualifying-day count
    as ``prior_paid_qualifying_days`` to enforce the 28-week maximum.
    """

    average_weekly_earnings = _decimal(
        average_weekly_earnings,
        "Average weekly earnings",
    )
    if average_weekly_earnings < ZERO:
        raise ValueError("Average weekly earnings cannot be negative.")

    if not isinstance(qualifying_days_per_week, int) or isinstance(
        qualifying_days_per_week,
        bool,
    ):
        raise ValueError("Qualifying days per week must be an integer.")
    if not 1 <= qualifying_days_per_week <= 7:
        raise ValueError("Qualifying days per week must be between 1 and 7.")

    for value, field_name in (
        (qualifying_days_sick, "Qualifying days sick"),
        (prior_paid_qualifying_days, "Prior paid qualifying days"),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{field_name} must be an integer.")
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative.")

    if sickness_start_date is not None:
        if not isinstance(sickness_start_date, date):
            raise ValueError("Sickness start date must be a date.")
        if sickness_start_date < TAX_YEAR_START_2026_27:
            raise ValueError(
                "Absences starting before 6 April 2026 require HMRC "
                "transitional SSP rules."
            )
        if sickness_start_date > TAX_YEAR_END_2026_27:
            raise ValueError(
                "The 2026/27 SSP routine only supports starts through "
                "5 April 2027."
            )

    earnings_based_rate = (
        average_weekly_earnings * SSP_EARNINGS_PERCENTAGE_2026_27
    )
    unrounded_weekly_rate = min(
        SSP_WEEKLY_CAP_2026_27,
        earnings_based_rate,
    )
    weekly_rate = _money(unrounded_weekly_rate)
    maximum_qualifying_days = SSP_MAX_WEEKS * qualifying_days_per_week
    remaining_before_period = max(
        0,
        maximum_qualifying_days - prior_paid_qualifying_days,
    )
    payable_days = min(qualifying_days_sick, remaining_before_period)
    daily_rate_unrounded = (
        unrounded_weekly_rate / Decimal(qualifying_days_per_week)
    )
    amount = _money(daily_rate_unrounded * payable_days)
    remaining_after_period = max(0, remaining_before_period - payable_days)

    return StatutorySickPayResult(
        tax_year="2026/27",
        average_weekly_earnings=_money(average_weekly_earnings),
        weekly_rate=weekly_rate,
        qualifying_days_per_week=qualifying_days_per_week,
        qualifying_days_sick=qualifying_days_sick,
        payable_qualifying_days=payable_days,
        prior_paid_qualifying_days=prior_paid_qualifying_days,
        remaining_qualifying_days=remaining_after_period,
        daily_rate_unrounded=daily_rate_unrounded,
        amount=amount,
        weekly_cap_applied=(
            earnings_based_rate > SSP_WEEKLY_CAP_2026_27
        ),
        waiting_days_applied=0,
    )
