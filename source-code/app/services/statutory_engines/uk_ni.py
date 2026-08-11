"""Monthly Class 1 National Insurance for UK tax year 2026/27."""

from dataclasses import dataclass
from decimal import Decimal

from app.services.payroll_calculator import money


ZERO = Decimal("0.00")
PRIMARY_THRESHOLD = Decimal("1048.00")
SECONDARY_THRESHOLD = Decimal("417.00")
FREEPORT_UPPER_SECONDARY_THRESHOLD = Decimal("2083.00")
UPPER_EARNINGS_LIMIT = Decimal("4189.00")
UPPER_SECONDARY_THRESHOLD = Decimal("4189.00")

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


@dataclass(frozen=True)
class Class1NIResult:
    """Auditable employee and employer Class 1 NI result."""

    category: str
    ni_earnings: Decimal
    employee_ni: Decimal
    employer_ni: Decimal


def normalise_ni_category(category):
    """Return a supported HMRC category letter or raise a clear error."""

    normalised = str(category or "A").strip().upper()
    if normalised not in SUPPORTED_CATEGORIES:
        raise ValueError(
            f"Unsupported UK National Insurance category: {normalised or '(blank)'}."
        )
    return normalised


def _band_earnings(earnings, lower, upper=None):
    if earnings <= lower:
        return ZERO
    if upper is None:
        return earnings - lower
    return min(earnings, upper) - lower


def calculate_employee_class_1(earnings, category="A"):
    """Calculate monthly primary Class 1 contributions."""

    pay = money(earnings)
    if pay < ZERO:
        raise ValueError("National Insurance earnings cannot be negative.")

    letter = normalise_ni_category(category)
    if letter in NO_EMPLOYEE_NI:
        return ZERO

    if letter in REDUCED_EMPLOYEE_CATEGORIES:
        main_rate = REDUCED_EMPLOYEE_RATE
    elif letter in DEFERRED_EMPLOYEE_CATEGORIES:
        main_rate = DEFERRED_EMPLOYEE_RATE
    else:
        main_rate = STANDARD_EMPLOYEE_RATE

    main_band = _band_earnings(
        pay,
        PRIMARY_THRESHOLD,
        UPPER_EARNINGS_LIMIT,
    )
    upper_band = _band_earnings(pay, UPPER_EARNINGS_LIMIT)
    return money(
        main_band * main_rate
        + upper_band * UPPER_EMPLOYEE_RATE
    )


def calculate_employer_class_1(earnings, category="A"):
    """Calculate monthly secondary Class 1 contributions."""

    pay = money(earnings)
    if pay < ZERO:
        raise ValueError("National Insurance earnings cannot be negative.")

    letter = normalise_ni_category(category)
    if letter in STANDARD_EMPLOYER_CATEGORIES:
        threshold = SECONDARY_THRESHOLD
    elif letter in FREEPORT_EMPLOYER_CATEGORIES:
        threshold = FREEPORT_UPPER_SECONDARY_THRESHOLD
    elif letter in UPPER_SECONDARY_EMPLOYER_CATEGORIES:
        threshold = UPPER_SECONDARY_THRESHOLD
    else:  # Defensive: normalise_ni_category already validates the set.
        raise ValueError(f"Unsupported UK National Insurance category: {letter}.")

    return money(_band_earnings(pay, threshold) * EMPLOYER_RATE)


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
