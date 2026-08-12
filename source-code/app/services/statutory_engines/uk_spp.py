"""United Kingdom Statutory Paternity Pay for the 2026/27 rate year."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0.00")
PENNY = Decimal("0.01")
SPP_STANDARD_WEEKLY_RATE_2026_27 = Decimal("194.32")
SPP_EARNINGS_PERCENTAGE = Decimal("0.90")
SPP_LOWER_EARNINGS_LIMIT_2026_27 = Decimal("129.00")
SPP_MAX_WEEKS = 2
SPP_RATE_YEAR_START_2026_27 = date(2026, 4, 5)
SPP_RATE_YEAR_END_2026_27 = date(2027, 4, 4)


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
class StatutoryPaternityPayResult:
    """Auditable SPP result for one payroll-period allocation."""

    rate_year: str
    average_weekly_earnings: Decimal
    lower_earnings_limit: Decimal
    eligible_by_earnings: bool
    weekly_rate: Decimal
    paid_days_requested: int
    payable_days: int
    prior_paid_days: int
    remaining_paid_days: int
    amount: Decimal
    standard_rate_cap_applied: bool


def calculate_spp_2026_27(
    *,
    average_weekly_earnings,
    paid_days,
    prior_paid_days=0,
    payment_date=None,
):
    """Calculate SPP payable under the rate applying from 5 April 2026.

    SPP is a weekly payment, payable for a maximum of two weeks and
    apportioned here by calendar day so payroll-period boundaries remain
    accurate. The caller owns relationship, employment-continuity, notice,
    birth or adoption evidence, leave-block validity, and the usage window.
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
        if not SPP_RATE_YEAR_START_2026_27 <= payment_date <= SPP_RATE_YEAR_END_2026_27:
            raise ValueError(
                "The 2026/27 SPP routine only supports payment dates from "
                "5 April 2026 through 4 April 2027."
            )

    eligible = awe >= SPP_LOWER_EARNINGS_LIMIT_2026_27
    ninety_percent = awe * SPP_EARNINGS_PERCENTAGE
    weekly_rate_unrounded = min(SPP_STANDARD_WEEKLY_RATE_2026_27, ninety_percent)
    maximum_days = SPP_MAX_WEEKS * 7
    remaining_before_period = max(0, maximum_days - prior_paid_days)
    payable_days = min(paid_days, remaining_before_period) if eligible else 0
    amount = _money((weekly_rate_unrounded / Decimal(7)) * payable_days)

    return StatutoryPaternityPayResult(
        rate_year="2026/27",
        average_weekly_earnings=_money(awe),
        lower_earnings_limit=SPP_LOWER_EARNINGS_LIMIT_2026_27,
        eligible_by_earnings=eligible,
        weekly_rate=_money(weekly_rate_unrounded),
        paid_days_requested=paid_days,
        payable_days=payable_days,
        prior_paid_days=prior_paid_days,
        remaining_paid_days=max(0, remaining_before_period - payable_days),
        amount=amount,
        standard_rate_cap_applied=(
            ninety_percent > SPP_STANDARD_WEEKLY_RATE_2026_27
        ),
    )
