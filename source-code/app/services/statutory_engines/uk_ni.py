"""Class 1 National Insurance for UK tax year 2026/27."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from app.services.payroll_calculator import money


ZERO = Decimal("0.00")
PRIMARY_THRESHOLD = Decimal("1048.00")
SECONDARY_THRESHOLD = Decimal("417.00")
FREEPORT_UPPER_SECONDARY_THRESHOLD = Decimal("2083.00")
UPPER_EARNINGS_LIMIT = Decimal("4189.00")
UPPER_SECONDARY_THRESHOLD = Decimal("4189.00")

ANNUAL_PRIMARY_THRESHOLD = Decimal("12570.00")
ANNUAL_SECONDARY_THRESHOLD = Decimal("5000.00")
ANNUAL_FREEPORT_UPPER_SECONDARY_THRESHOLD = Decimal("25000.00")
ANNUAL_UPPER_EARNINGS_LIMIT = Decimal("50270.00")
ANNUAL_UPPER_SECONDARY_THRESHOLD = Decimal("50270.00")

STANDARD_EMPLOYEE_RATE = Decimal("0.08")
REDUCED_EMPLOYEE_RATE = Decimal("0.0185")
DEFERRED_EMPLOYEE_RATE = Decimal("0.02")
UPPER_EMPLOYEE_RATE = Decimal("0.02")
EMPLOYER_RATE = Decimal("0.15")

SUPPORTED_CATEGORIES = frozenset(
    {"A", "B", "C", "D", "E", "F", "H", "I", "J", "K", "L", "M", "N", "S", "V", "Z"}
)
NO_EMPLOYEE_NI = frozenset({"C", "K", "S"})
REDUCED_EMPLOYEE_CATEGORIES = frozenset({"B", "E", "I"})
DEFERRED_EMPLOYEE_CATEGORIES = frozenset({"D", "J", "L", "Z"})
STANDARD_EMPLOYER_CATEGORIES = frozenset({"A", "B", "C", "J"})
FREEPORT_EMPLOYER_CATEGORIES = frozenset({"D", "E", "F", "I", "K", "L", "N", "S"})
UPPER_SECONDARY_EMPLOYER_CATEGORIES = frozenset({"H", "M", "V", "Z"})
DIRECTOR_METHODS = frozenset({"STANDARD", "ALTERNATIVE"})


@dataclass(frozen=True)
class Class1NIResult:
    """Auditable employee and employer Class 1 NI result."""

    category: str
    ni_earnings: Decimal
    employee_ni: Decimal
    employer_ni: Decimal


@dataclass(frozen=True)
class DirectorClass1NIResult:
    """Current and year-to-date Class 1 NI for a company director."""

    category: str
    method: str
    appointment_week: int
    earnings_period_weeks: int
    current_earnings: Decimal
    earnings_to_date: Decimal
    employee_ni: Decimal
    employer_ni: Decimal
    employee_ni_to_date: Decimal
    employer_ni_to_date: Decimal
    final_reconciliation: bool


def normalise_ni_category(category):
    """Return a supported HMRC category letter or raise a clear error."""

    normalised = str(category or "A").strip().upper()
    if normalised not in SUPPORTED_CATEGORIES:
        raise ValueError(
            f"Unsupported UK National Insurance category: {normalised or '(blank)'}."
        )
    return normalised


def normalise_director_method(method):
    normalised = str(method or "STANDARD").strip().upper()
    if normalised not in DIRECTOR_METHODS:
        raise ValueError(
            f"Unsupported UK director National Insurance method: {normalised or '(blank)'}."
        )
    return normalised


def _band_earnings(earnings, lower, upper=None):
    if earnings <= lower:
        return ZERO
    if upper is None:
        return earnings - lower
    return min(earnings, upper) - lower


def _employee_contribution(earnings, category, primary_threshold, upper_limit):
    if category in NO_EMPLOYEE_NI:
        return ZERO
    if category in REDUCED_EMPLOYEE_CATEGORIES:
        main_rate = REDUCED_EMPLOYEE_RATE
    elif category in DEFERRED_EMPLOYEE_CATEGORIES:
        main_rate = DEFERRED_EMPLOYEE_RATE
    else:
        main_rate = STANDARD_EMPLOYEE_RATE
    return money(
        _band_earnings(earnings, primary_threshold, upper_limit) * main_rate
        + _band_earnings(earnings, upper_limit) * UPPER_EMPLOYEE_RATE
    )


def _employer_threshold(category, standard, freeport, upper_secondary):
    if category in STANDARD_EMPLOYER_CATEGORIES:
        return standard
    if category in FREEPORT_EMPLOYER_CATEGORIES:
        return freeport
    if category in UPPER_SECONDARY_EMPLOYER_CATEGORIES:
        return upper_secondary
    raise ValueError(f"Unsupported UK National Insurance category: {category}.")


def _employer_contribution(earnings, category, standard, freeport, upper_secondary):
    threshold = _employer_threshold(category, standard, freeport, upper_secondary)
    return money(_band_earnings(earnings, threshold) * EMPLOYER_RATE)


def calculate_employee_class_1(earnings, category="A"):
    """Calculate monthly primary Class 1 contributions."""

    pay = money(earnings)
    if pay < ZERO:
        raise ValueError("National Insurance earnings cannot be negative.")
    letter = normalise_ni_category(category)
    return _employee_contribution(pay, letter, PRIMARY_THRESHOLD, UPPER_EARNINGS_LIMIT)


def calculate_employer_class_1(earnings, category="A"):
    """Calculate monthly secondary Class 1 contributions."""

    pay = money(earnings)
    if pay < ZERO:
        raise ValueError("National Insurance earnings cannot be negative.")
    letter = normalise_ni_category(category)
    return _employer_contribution(
        pay,
        letter,
        SECONDARY_THRESHOLD,
        FREEPORT_UPPER_SECONDARY_THRESHOLD,
        UPPER_SECONDARY_THRESHOLD,
    )


def calculate_monthly_class_1(earnings, category="A"):
    """Return employee and employer monthly Class 1 contributions."""

    pay = money(earnings)
    letter = normalise_ni_category(category)
    return Class1NIResult(
        category=letter,
        ni_earnings=pay,
        employee_ni=calculate_employee_class_1(pay, letter),
        employer_ni=calculate_employer_class_1(pay, letter),
    )


def director_earnings_period_weeks(appointment_week=1):
    """Return HMRC's 52-week annual or pro-rata director earnings period."""

    try:
        week = int(appointment_week)
    except (TypeError, ValueError) as error:
        raise ValueError("Director appointment week must be from 1 to 53.") from error
    if week < 1 or week > 53:
        raise ValueError("Director appointment week must be from 1 to 53.")
    return 52 if week == 1 else max(1, 53 - week)


def _pro_rata_threshold(annual_threshold, weeks):
    if weeks == 52:
        return annual_threshold
    return (
        annual_threshold / Decimal("52") * Decimal(weeks)
    ).quantize(Decimal("1"), rounding=ROUND_CEILING)


def director_thresholds(appointment_week=1):
    """Return annual or HMRC-rounded pro-rata thresholds for a director."""

    weeks = director_earnings_period_weeks(appointment_week)
    return {
        "weeks": weeks,
        "primary": _pro_rata_threshold(ANNUAL_PRIMARY_THRESHOLD, weeks),
        "secondary": _pro_rata_threshold(ANNUAL_SECONDARY_THRESHOLD, weeks),
        "freeport": _pro_rata_threshold(
            ANNUAL_FREEPORT_UPPER_SECONDARY_THRESHOLD, weeks
        ),
        "upper_earnings": _pro_rata_threshold(
            ANNUAL_UPPER_EARNINGS_LIMIT, weeks
        ),
        "upper_secondary": _pro_rata_threshold(
            ANNUAL_UPPER_SECONDARY_THRESHOLD, weeks
        ),
    }


def _director_annual_liability(earnings_to_date, category, appointment_week):
    thresholds = director_thresholds(appointment_week)
    employee = _employee_contribution(
        earnings_to_date,
        category,
        thresholds["primary"],
        thresholds["upper_earnings"],
    )
    employer = _employer_contribution(
        earnings_to_date,
        category,
        thresholds["secondary"],
        thresholds["freeport"],
        thresholds["upper_secondary"],
    )
    return employee, employer, thresholds["weeks"]


def calculate_director_class_1(
    current_earnings,
    *,
    category="A",
    method="STANDARD",
    appointment_week=1,
    prior_earnings=ZERO,
    prior_employee_ni=ZERO,
    prior_employer_ni=ZERO,
    final_pay_period=False,
):
    """Calculate current Class 1 NI using either HMRC director method.

    The standard method assesses cumulative earnings against annual (or pro-rata
    annual) thresholds every pay period. The alternative method uses ordinary
    periodic Class 1 calculations until the final payment, when it reconciles
    total liability against the annual director thresholds.
    """

    current = money(current_earnings)
    prior_pay = money(prior_earnings)
    prior_employee = money(prior_employee_ni)
    prior_employer = money(prior_employer_ni)
    for name, value in (
        ("Current NI earnings", current),
        ("Prior NI earnings", prior_pay),
        ("Prior employee NI", prior_employee),
        ("Prior employer NI", prior_employer),
    ):
        if value < ZERO:
            raise ValueError(f"{name} cannot be negative.")

    letter = normalise_ni_category(category)
    calculation_method = normalise_director_method(method)
    weeks = director_earnings_period_weeks(appointment_week)
    earnings_to_date = money(prior_pay + current)
    reconcile = calculation_method == "STANDARD" or bool(final_pay_period)

    if reconcile:
        employee_to_date, employer_to_date, weeks = _director_annual_liability(
            earnings_to_date, letter, appointment_week
        )
        employee_now = money(employee_to_date - prior_employee)
        employer_now = money(employer_to_date - prior_employer)
    else:
        periodic = calculate_monthly_class_1(current, letter)
        employee_now = periodic.employee_ni
        employer_now = periodic.employer_ni
        employee_to_date = money(prior_employee + employee_now)
        employer_to_date = money(prior_employer + employer_now)

    return DirectorClass1NIResult(
        category=letter,
        method=calculation_method,
        appointment_week=int(appointment_week),
        earnings_period_weeks=weeks,
        current_earnings=current,
        earnings_to_date=earnings_to_date,
        employee_ni=employee_now,
        employer_ni=employer_now,
        employee_ni_to_date=employee_to_date,
        employer_ni_to_date=employer_to_date,
        final_reconciliation=bool(final_pay_period),
    )
