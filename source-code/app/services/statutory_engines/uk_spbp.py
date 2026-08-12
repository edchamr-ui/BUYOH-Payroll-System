"""United Kingdom Statutory Parental Bereavement Pay for 2026/27."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0.00")
PENNY = Decimal("0.01")
SPBP_STANDARD_WEEKLY_RATE_2026_27 = Decimal("194.32")
SPBP_EARNINGS_PERCENTAGE = Decimal("0.90")
SPBP_LOWER_EARNINGS_LIMIT_2026_27 = Decimal("129.00")
SPBP_MAX_WEEKS = 2
SPBP_MAX_DAYS = SPBP_MAX_WEEKS * 7
SPBP_RATE_YEAR_START_2026_27 = date(2026, 4, 5)
SPBP_RATE_YEAR_END_2026_27 = date(2027, 4, 4)


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
class StatutoryParentalBereavementPayResult:
    """Auditable SPBP result for one payroll-period allocation."""

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


def calculate_spbp_2026_27(
    *,
    average_weekly_earnings,
    paid_days,
    prior_paid_days=0,
    payment_date=None,
):
    """Calculate SPBP payable under the 2026/27 statutory rate.

    SPBP lasts for one or two complete weeks. Seven-day apportionment is
    supported so an employer can align a statutory week across payroll-period
    boundaries. The caller owns bereaved-parent eligibility, employment and
    notice checks, evidence, leave-block validity, and the 56-week usage window.
    """

    awe = _decimal(average_weekly_earnings, "Average weekly earnings")
    if awe < ZERO:
        raise ValueError("Average weekly earnings cannot be negative.")

    paid_days = _days(paid_days, "Paid days")
    prior_paid_days = _days(prior_paid_days, "Prior paid days")

    if payment_date is not None:
        if not isinstance(payment_date, date):
            raise ValueError("Payment date must be a date.")
        if not (
            SPBP_RATE_YEAR_START_2026_27
            <= payment_date
            <= SPBP_RATE_YEAR_END_2026_27
        ):
            raise ValueError(
                "The 2026/27 SPBP routine only supports payment dates from "
                "5 April 2026 through 4 April 2027."
            )

    eligible = awe >= SPBP_LOWER_EARNINGS_LIMIT_2026_27
    ninety_percent = awe * SPBP_EARNINGS_PERCENTAGE
    weekly_rate_unrounded = min(
        SPBP_STANDARD_WEEKLY_RATE_2026_27,
        ninety_percent,
    )
    remaining_before_period = max(0, SPBP_MAX_DAYS - prior_paid_days)
    payable_days = min(paid_days, remaining_before_period) if eligible else 0
    amount = _money((weekly_rate_unrounded / Decimal(7)) * payable_days)

    return StatutoryParentalBereavementPayResult(
        rate_year="2026/27",
        average_weekly_earnings=_money(awe),
        lower_earnings_limit=SPBP_LOWER_EARNINGS_LIMIT_2026_27,
        eligible_by_earnings=eligible,
        weekly_rate=_money(weekly_rate_unrounded),
        paid_days_requested=paid_days,
        payable_days=payable_days,
        prior_paid_days=prior_paid_days,
        remaining_paid_days=max(0, remaining_before_period - payable_days),
        amount=amount,
        standard_rate_cap_applied=(
            ninety_percent > SPBP_STANDARD_WEEKLY_RATE_2026_27
        ),
    )
