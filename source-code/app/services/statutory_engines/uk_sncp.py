"""United Kingdom Statutory Neonatal Care Pay for 2026/27."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0.00")
PENNY = Decimal("0.01")
SNCP_STANDARD_WEEKLY_RATE_2026_27 = Decimal("194.32")
SNCP_EARNINGS_PERCENTAGE = Decimal("0.90")
SNCP_LOWER_EARNINGS_LIMIT_2026_27 = Decimal("129.00")
SNCP_MAX_WEEKS = 12
SNCP_MAX_DAYS = SNCP_MAX_WEEKS * 7
SNCP_RATE_YEAR_START_2026_27 = date(2026, 4, 5)
SNCP_RATE_YEAR_END_2026_27 = date(2027, 4, 4)


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


def _integer(value, field_name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return value


@dataclass(frozen=True)
class StatutoryNeonatalCarePayResult:
    """Auditable SNCP result for one payroll-period allocation."""

    rate_year: str
    average_weekly_earnings: Decimal
    lower_earnings_limit: Decimal
    eligible_by_earnings: bool
    weekly_rate: Decimal
    accrued_weeks: int
    accrued_days: int
    paid_days_requested: int
    payable_days: int
    prior_paid_days: int
    remaining_accrued_days: int
    amount: Decimal
    standard_rate_cap_applied: bool


def calculate_sncp_2026_27(
    *,
    average_weekly_earnings,
    accrued_weeks,
    paid_days,
    prior_paid_days=0,
    payment_date=None,
):
    """Calculate SNCP from an employer-confirmed care-week entitlement.

    Each seven consecutive full days of neonatal care accrues one week, up to
    twelve weeks. ``paid_days`` supports aligning a complete statutory week
    across payroll periods; it does not make partial-week leave eligible. The
    operational layer owns care, relationship, service, notice, declaration,
    leave-block and 68-week-window checks.
    """

    awe = _decimal(average_weekly_earnings, "Average weekly earnings")
    if awe < ZERO:
        raise ValueError("Average weekly earnings cannot be negative.")

    accrued_weeks = _integer(accrued_weeks, "Accrued weeks")
    paid_days = _integer(paid_days, "Paid days")
    prior_paid_days = _integer(prior_paid_days, "Prior paid days")
    if accrued_weeks > SNCP_MAX_WEEKS:
        raise ValueError("Accrued weeks cannot exceed 12 weeks.")

    if payment_date is not None:
        if not isinstance(payment_date, date):
            raise ValueError("Payment date must be a date.")
        if not (
            SNCP_RATE_YEAR_START_2026_27
            <= payment_date
            <= SNCP_RATE_YEAR_END_2026_27
        ):
            raise ValueError(
                "The 2026/27 SNCP routine only supports payment dates from "
                "5 April 2026 through 4 April 2027."
            )

    eligible = awe >= SNCP_LOWER_EARNINGS_LIMIT_2026_27
    ninety_percent = awe * SNCP_EARNINGS_PERCENTAGE
    weekly_rate_unrounded = min(
        SNCP_STANDARD_WEEKLY_RATE_2026_27,
        ninety_percent,
    )
    accrued_days = accrued_weeks * 7
    remaining_before_period = max(0, accrued_days - prior_paid_days)
    payable_days = min(paid_days, remaining_before_period) if eligible else 0
    amount = _money((weekly_rate_unrounded / Decimal(7)) * payable_days)

    return StatutoryNeonatalCarePayResult(
        rate_year="2026/27",
        average_weekly_earnings=_money(awe),
        lower_earnings_limit=SNCP_LOWER_EARNINGS_LIMIT_2026_27,
        eligible_by_earnings=eligible,
        weekly_rate=_money(weekly_rate_unrounded),
        accrued_weeks=accrued_weeks,
        accrued_days=accrued_days,
        paid_days_requested=paid_days,
        payable_days=payable_days,
        prior_paid_days=prior_paid_days,
        remaining_accrued_days=max(0, remaining_before_period - payable_days),
        amount=amount,
        standard_rate_cap_applied=(
            ninety_percent > SNCP_STANDARD_WEEKLY_RATE_2026_27
        ),
    )
