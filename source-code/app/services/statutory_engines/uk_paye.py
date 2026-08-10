"""HMRC-compatible UK monthly PAYE calculations for 2026/27."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN

from app.services.statutory_engines.uk_tax_codes import (
    BASIS_CUMULATIVE,
    KIND_ALLOWANCE,
    KIND_K_CODE,
    REGION_ENGLAND_NI,
    REGION_SCOTLAND,
    REGION_WALES,
    parse_uk_tax_code,
)


ZERO = Decimal("0.00")
PENNY = Decimal("0.01")
POUND = Decimal("1")
MONTHS = Decimal("12")
MAX_DEDUCTION_RATE = Decimal("0.50")


class UKPayeCalculationError(ValueError):
    """Raised when a UK PAYE calculation input is invalid."""


@dataclass(frozen=True)
class TaxParameters:
    """HMRC PAYE routine parameters for one tax region."""

    rates: tuple[Decimal, ...]
    cumulative_bandwidths: tuple[Decimal, ...]
    cumulative_annual_taxes: tuple[Decimal, ...]
    basic_rate_pointer: int


@dataclass(frozen=True)
class UKPayeResult:
    """Auditable result of one monthly PAYE calculation."""

    tax_code: str
    tax_region: str
    tax_basis: str
    tax_month: int
    current_taxable_pay: Decimal
    cumulative_pay_to_date: Decimal
    pay_adjustment_for_month: Decimal
    pay_adjustment_to_date: Decimal
    unrounded_taxable_pay_to_date: Decimal
    rounded_taxable_pay_to_date: Decimal
    table_tax_due_to_date: Decimal
    prior_tax_paid_to_date: Decimal
    paye_before_regulatory_limit: Decimal
    regulatory_limit: Decimal
    regulatory_limit_applied: bool
    paye: Decimal
    tax_paid_to_date: Decimal

    @property
    def is_refund(self):
        return self.paye < ZERO


REST_OF_UK = TaxParameters(
    rates=(
        Decimal("0.10"),
        Decimal("0.20"),
        Decimal("0.40"),
        Decimal("0.45"),
    ),
    cumulative_bandwidths=(
        Decimal("0"),
        Decimal("37700"),
        Decimal("125140"),
    ),
    cumulative_annual_taxes=(
        Decimal("0"),
        Decimal("7540"),
        Decimal("42516"),
    ),
    basic_rate_pointer=1,
)

SCOTLAND = TaxParameters(
    rates=(
        Decimal("0.19"),
        Decimal("0.20"),
        Decimal("0.21"),
        Decimal("0.42"),
        Decimal("0.45"),
        Decimal("0.48"),
    ),
    cumulative_bandwidths=(
        Decimal("3967"),
        Decimal("16956"),
        Decimal("31092"),
        Decimal("62430"),
        Decimal("125140"),
    ),
    cumulative_annual_taxes=(
        Decimal("753.73"),
        Decimal("3351.53"),
        Decimal("6320.09"),
        Decimal("19482.05"),
        Decimal("47701.55"),
    ),
    basic_rate_pointer=1,
)

PARAMETERS_BY_REGION = {
    REGION_ENGLAND_NI: REST_OF_UK,
    REGION_SCOTLAND: SCOTLAND,
    REGION_WALES: REST_OF_UK,
}

SPECIAL_RATE_OFFSETS = {
    "BR": 0,
    "D0": 1,
    "D1": 2,
    "D2": 3,
    "D3": 4,
}


def _decimal(name, value, *, non_negative=True):
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise UKPayeCalculationError(
            f"{name} must be a valid monetary amount."
        ) from error

    if not result.is_finite():
        raise UKPayeCalculationError(
            f"{name} must be a finite monetary amount."
        )

    if non_negative and result < ZERO:
        raise UKPayeCalculationError(
            f"{name} cannot be negative."
        )

    return result


def _money_down(value):
    return Decimal(value).quantize(PENNY, rounding=ROUND_DOWN)


def _whole_pounds_down(value):
    return Decimal(value).quantize(POUND, rounding=ROUND_DOWN)


def _pounds_up(value):
    return Decimal(value).quantize(POUND, rounding=ROUND_CEILING)


def _table_a_month_one(code_number):
    """Return HMRC Table A Month 1 free/additional pay."""

    if code_number == 0:
        return ZERO

    quotient, remainder = divmod(code_number - 1, 500)
    remainder += 1

    remainder_value = (
        Decimal(remainder * 10 + 9) / MONTHS
    ).quantize(PENNY, rounding=ROUND_CEILING)

    return money(
        Decimal(quotient) * Decimal("416.67")
        + remainder_value
    )


def money(value):
    return Decimal(value).quantize(PENNY)


def _scaled_parameters(parameters, tax_month):
    fraction = Decimal(tax_month) / MONTHS

    exact_thresholds = tuple(
        bandwidth * fraction
        for bandwidth in parameters.cumulative_bandwidths
    )
    comparison_thresholds = tuple(
        _pounds_up(value)
        for value in exact_thresholds
    )
    threshold_taxes = tuple(
        annual_tax * fraction
        for annual_tax in parameters.cumulative_annual_taxes
    )

    return (
        exact_thresholds,
        comparison_thresholds,
        threshold_taxes,
    )


def _progressive_tax(taxable_pay, parameters, tax_month):
    if taxable_pay <= ZERO:
        return ZERO

    rounded_pay = _whole_pounds_down(taxable_pay)
    (
        exact_thresholds,
        comparison_thresholds,
        threshold_taxes,
    ) = _scaled_parameters(parameters, tax_month)

    formula_index = len(comparison_thresholds)
    for index, threshold in enumerate(comparison_thresholds):
        if taxable_pay <= threshold:
            formula_index = index
            break

    if formula_index == 0:
        tax = rounded_pay * parameters.rates[0]
    else:
        tax = (
            threshold_taxes[formula_index - 1]
            + (
                rounded_pay
                - exact_thresholds[formula_index - 1]
            )
            * parameters.rates[formula_index]
        )

    return _money_down(tax)


def _special_tax(parsed_code, pay, tax_month):
    special_code = parsed_code.special_code

    if special_code == "NT":
        return ZERO

    if special_code == "0T":
        parameters = PARAMETERS_BY_REGION[parsed_code.region]
        return _progressive_tax(pay, parameters, tax_month)

    parameters = PARAMETERS_BY_REGION[parsed_code.region]
    offset = SPECIAL_RATE_OFFSETS[special_code]
    rate_index = parameters.basic_rate_pointer + offset

    if rate_index >= len(parameters.rates):
        raise UKPayeCalculationError(
            f"Tax code {parsed_code.normalized_code} has no "
            "configured 2026/27 rate."
        )

    return _money_down(
        _whole_pounds_down(pay) * parameters.rates[rate_index]
    )


def calculate_monthly_paye(
    *,
    tax_code,
    current_taxable_pay,
    tax_month,
    default_basis=BASIS_CUMULATIVE,
    prior_taxable_pay=ZERO,
    prior_tax_paid=ZERO,
    current_pay_for_regulatory_limit=None,
    payrolled_benefits=ZERO,
):
    """Calculate monthly PAYE using HMRC PAYErout v24.0."""

    try:
        month = int(tax_month)
    except (TypeError, ValueError) as error:
        raise UKPayeCalculationError(
            "UK tax month must be an integer from 1 to 12."
        ) from error

    if month < 1 or month > 12 or str(tax_month).strip() != str(month):
        raise UKPayeCalculationError(
            "UK tax month must be an integer from 1 to 12."
        )

    current_pay = _decimal("Current taxable pay", current_taxable_pay)
    prior_pay = _decimal("Prior taxable pay", prior_taxable_pay)
    prior_tax = _decimal(
        "Prior tax paid", prior_tax_paid, non_negative=False
    )
    benefits = _decimal("Payrolled benefits", payrolled_benefits)

    if current_pay_for_regulatory_limit is None:
        limit_pay = current_pay
    else:
        limit_pay = _decimal(
            "Current pay for regulatory limit",
            current_pay_for_regulatory_limit,
        )

    if benefits > limit_pay:
        raise UKPayeCalculationError(
            "Payrolled benefits cannot exceed current pay used "
            "for the regulatory limit."
        )

    parsed_code = parse_uk_tax_code(
        tax_code,
        default_basis=default_basis,
    )
    cumulative = parsed_code.basis == BASIS_CUMULATIVE
    periods = month if cumulative else 1
    pay_to_date = prior_pay + current_pay if cumulative else current_pay

    adjustment_for_month = ZERO
    adjustment_to_date = ZERO
    unrounded_taxable = pay_to_date

    if parsed_code.kind in {KIND_ALLOWANCE, KIND_K_CODE}:
        adjustment_for_month = _table_a_month_one(
            parsed_code.code_number
        )
        adjustment_to_date = adjustment_for_month * periods

        if parsed_code.kind == KIND_ALLOWANCE:
            unrounded_taxable = pay_to_date - adjustment_to_date
        else:
            unrounded_taxable = pay_to_date + adjustment_to_date

        table_tax = _progressive_tax(
            max(ZERO, unrounded_taxable),
            PARAMETERS_BY_REGION[parsed_code.region],
            periods,
        )
    else:
        table_tax = _special_tax(parsed_code, pay_to_date, periods)

    table_tax = money(table_tax)
    paye_before_limit = (
        table_tax - prior_tax if cumulative else table_tax
    )

    regulatory_limit = _money_down(
        (limit_pay - benefits) * MAX_DEDUCTION_RATE
    )
    limit_applied = paye_before_limit > regulatory_limit
    paye = regulatory_limit if limit_applied else paye_before_limit
    paye = money(paye)
    tax_paid_to_date = (
        prior_tax + paye if cumulative else paye
    )

    return UKPayeResult(
        tax_code=parsed_code.normalized_code,
        tax_region=parsed_code.region,
        tax_basis=parsed_code.basis,
        tax_month=month,
        current_taxable_pay=money(current_pay),
        cumulative_pay_to_date=money(pay_to_date),
        pay_adjustment_for_month=money(adjustment_for_month),
        pay_adjustment_to_date=money(adjustment_to_date),
        unrounded_taxable_pay_to_date=money(
            max(ZERO, unrounded_taxable)
        ),
        rounded_taxable_pay_to_date=money(
            _whole_pounds_down(max(ZERO, unrounded_taxable))
        ),
        table_tax_due_to_date=table_tax,
        prior_tax_paid_to_date=money(prior_tax),
        paye_before_regulatory_limit=money(paye_before_limit),
        regulatory_limit=money(regulatory_limit),
        regulatory_limit_applied=limit_applied,
        paye=paye,
        tax_paid_to_date=money(tax_paid_to_date),
    )


def calculate_monthly_paye_from_profile(
    *,
    tax_profile,
    current_taxable_pay,
    tax_month,
    prior_taxable_pay=ZERO,
    prior_tax_paid=ZERO,
    current_pay_for_regulatory_limit=None,
    payrolled_benefits=ZERO,
):
    """Calculate PAYE from an EmployeeUKTaxProfile-like object."""

    if tax_profile is None:
        raise UKPayeCalculationError(
            "A UK employee tax profile is required."
        )

    result = calculate_monthly_paye(
        tax_code=getattr(tax_profile, "tax_code", None),
        default_basis=getattr(
            tax_profile, "tax_basis", BASIS_CUMULATIVE
        ),
        current_taxable_pay=current_taxable_pay,
        tax_month=tax_month,
        prior_taxable_pay=prior_taxable_pay,
        prior_tax_paid=prior_tax_paid,
        current_pay_for_regulatory_limit=(
            current_pay_for_regulatory_limit
        ),
        payrolled_benefits=payrolled_benefits,
    )

    configured_region = str(
        getattr(tax_profile, "tax_region", result.tax_region)
        or result.tax_region
    ).strip().upper()

    if configured_region != result.tax_region:
        raise UKPayeCalculationError(
            "The UK tax profile region does not match "
            f"tax code {result.tax_code}."
        )

    return result
