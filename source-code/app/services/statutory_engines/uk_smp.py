"""United Kingdom Statutory Maternity Pay for the 2026/27 rate year."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0.00")
PENNY = Decimal("0.01")
SMP_STANDARD_WEEKLY_RATE_2026_27 = Decimal("194.32")
SMP_EARNINGS_PERCENTAGE = Decimal("0.90")
SMP_LOWER_EARNINGS_LIMIT_2026_27 = Decimal("129.00")
SMP_HIGHER_RATE_WEEKS = 6
SMP_MAX_WEEKS = 39
SMP_RATE_YEAR_START_2026_27 = date(2026, 4, 5)
SMP_RATE_YEAR_END_2026_27 = date(2027, 4, 4)


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
class StatutoryMaternityPayResult:
    """Auditable SMP result for one payroll-period allocation."""

    rate_year: str
    average_weekly_earnings: Decimal
    lower_earnings_limit: Decimal
    eligible_by_earnings: bool
    higher_weekly_rate: Decimal
    standard_weekly_rate: Decimal
    paid_days_requested: int
    payable_days: int
    prior_paid_days: int
    higher_rate_days: int
    standard_rate_days: int
    remaining_paid_days: int
    amount: Decimal
    standard_rate_cap_applied: bool


def calculate_smp_2026_27(
    *,
    average_weekly_earnings,
    paid_days,
    prior_paid_days=0,
    payment_date=None,
):
    """Calculate SMP payable under the rate applying from 5 April 2026.

    SMP is a weekly benefit apportioned by calendar day. ``paid_days`` is the
    number of SMP calendar days falling in this payroll calculation, while
    ``prior_paid_days`` is the cumulative number already allocated. The caller
    remains responsible for non-earnings eligibility, evidence, notice,
    employment continuity, and determining the maternity pay period.
    """

    awe = _decimal(average_weekly_earnings, "Average weekly earnings")
    if awe < ZERO:
        raise ValueError("Average weekly earnings cannot be negative.")

    for value, field_name in (
        (paid_days, "Paid days"),
        (prior_paid_days, "Prior paid days"),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{field_name} must be an integer.")
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative.")

    if payment_date is not None:
        if not isinstance(payment_date, date):
            raise ValueError("Payment date must be a date.")
        if not SMP_RATE_YEAR_START_2026_27 <= payment_date <= SMP_RATE_YEAR_END_2026_27:
            raise ValueError(
                "The 2026/27 SMP routine only supports payment dates from "
                "5 April 2026 through 4 April 2027."
            )

    eligible = awe >= SMP_LOWER_EARNINGS_LIMIT_2026_27
    higher_weekly_unrounded = awe * SMP_EARNINGS_PERCENTAGE
    standard_weekly_unrounded = min(
        SMP_STANDARD_WEEKLY_RATE_2026_27,
        higher_weekly_unrounded,
    )

    maximum_days = SMP_MAX_WEEKS * 7
    higher_rate_limit = SMP_HIGHER_RATE_WEEKS * 7
    remaining_before_period = max(0, maximum_days - prior_paid_days)
    payable_days = min(paid_days, remaining_before_period) if eligible else 0
    higher_days_remaining = max(0, higher_rate_limit - prior_paid_days)
    higher_rate_days = min(payable_days, higher_days_remaining)
    standard_rate_days = payable_days - higher_rate_days

    unrounded_amount = (
        (higher_weekly_unrounded / Decimal(7)) * higher_rate_days
        + (standard_weekly_unrounded / Decimal(7)) * standard_rate_days
    )
    amount = _money(unrounded_amount)
    remaining_after_period = max(0, remaining_before_period - payable_days)

    return StatutoryMaternityPayResult(
        rate_year="2026/27",
        average_weekly_earnings=_money(awe),
        lower_earnings_limit=SMP_LOWER_EARNINGS_LIMIT_2026_27,
        eligible_by_earnings=eligible,
        higher_weekly_rate=_money(higher_weekly_unrounded),
        standard_weekly_rate=_money(standard_weekly_unrounded),
        paid_days_requested=paid_days,
        payable_days=payable_days,
        prior_paid_days=prior_paid_days,
        higher_rate_days=higher_rate_days,
        standard_rate_days=standard_rate_days,
        remaining_paid_days=remaining_after_period,
        amount=amount,
        standard_rate_cap_applied=(
            higher_weekly_unrounded > SMP_STANDARD_WEEKLY_RATE_2026_27
        ),
    )
