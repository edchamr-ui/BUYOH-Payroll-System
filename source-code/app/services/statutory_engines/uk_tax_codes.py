"""UK PAYE tax-code parsing and validation."""

import re
from dataclasses import dataclass
from decimal import Decimal


ZERO = Decimal("0.00")

REGION_ENGLAND_NI = "ENGLAND_NI"
REGION_SCOTLAND = "SCOTLAND"
REGION_WALES = "WALES"

BASIS_CUMULATIVE = "CUMULATIVE"
BASIS_W1_M1 = "W1_M1"

KIND_ALLOWANCE = "ALLOWANCE"
KIND_K_CODE = "K_CODE"
KIND_SPECIAL = "SPECIAL"

REGION_PREFIXES = {
    "S": REGION_SCOTLAND,
    "C": REGION_WALES,
}

EMERGENCY_SUFFIXES = {
    "W1",
    "M1",
    "X",
    "NONCUM",
}

SPECIAL_CODES_BY_REGION = {
    REGION_ENGLAND_NI: {
        "BR",
        "D0",
        "D1",
        "NT",
        "0T",
    },
    REGION_SCOTLAND: {
        "BR",
        "D0",
        "D1",
        "D2",
        "D3",
        "NT",
        "0T",
    },
    REGION_WALES: {
        "BR",
        "D0",
        "D1",
        "NT",
        "0T",
    },
}

ALLOWANCE_PATTERN = re.compile(
    r"^(?P<number>[0-9]{1,4})(?P<suffix>[LMNT])$"
)

K_CODE_PATTERN = re.compile(
    r"^K(?P<number>[0-9]{1,4})$"
)


class UKTaxCodeError(ValueError):
    """Raised when a UK tax code is invalid or unsupported."""


@dataclass(frozen=True)
class ParsedUKTaxCode:
    """Normalized interpretation of one UK PAYE tax code."""

    raw_code: str
    normalized_code: str
    core_code: str
    region: str
    basis: str
    kind: str
    code_number: int | None
    suffix: str | None
    annual_allowance: Decimal
    annual_additional_pay: Decimal
    special_code: str | None

    @property
    def is_cumulative(self):
        """Return whether the code uses cumulative PAYE."""

        return self.basis == BASIS_CUMULATIVE

    @property
    def is_non_cumulative(self):
        """Return whether the code uses Week 1/Month 1 PAYE."""

        return self.basis == BASIS_W1_M1

    @property
    def is_k_code(self):
        """Return whether the code is a K code."""

        return self.kind == KIND_K_CODE

    @property
    def is_special(self):
        """Return whether the code is a special-rate code."""

        return self.kind == KIND_SPECIAL


def normalize_tax_code(value):
    """Return a consistently formatted tax-code string."""

    if value is None:
        raise UKTaxCodeError(
            "A UK tax code is required."
        )

    normalized = " ".join(
        str(value).strip().upper().split()
    )

    if not normalized:
        raise UKTaxCodeError(
            "A UK tax code is required."
        )

    return normalized


def _split_basis(normalized_code, default_basis):
    """Separate an emergency marker from the core tax code."""

    parts = normalized_code.split(" ")

    if (
        len(parts) == 2
        and parts[1] in EMERGENCY_SUFFIXES
    ):
        return parts[0], BASIS_W1_M1

    if len(parts) != 1:
        raise UKTaxCodeError(
            f"Invalid UK tax code format: "
            f"{normalized_code!r}."
        )

    if default_basis not in {
        BASIS_CUMULATIVE,
        BASIS_W1_M1,
    }:
        raise UKTaxCodeError(
            "UK tax basis must be CUMULATIVE or W1_M1."
        )

    return parts[0], default_basis


def _split_region(core_code):
    """Extract an optional Scottish or Welsh prefix."""

    if len(core_code) > 1:
        prefix = core_code[0]

        if prefix in REGION_PREFIXES:
            return (
                core_code[1:],
                REGION_PREFIXES[prefix],
            )

    return core_code, REGION_ENGLAND_NI


def _allowance_from_number(code_number):
    """
    Convert a standard numeric code into an annual allowance.

    For example, code 1257L represents £12,570.
    """

    return Decimal(code_number * 10).quantize(
        Decimal("0.01")
    )


def _additional_pay_from_k_number(code_number):
    """
    Convert a K-code number into annual additional taxable pay.

    Reversing HMRC's K-code construction means that K154
    represents £1,550 of additional taxable pay.
    """

    return Decimal((code_number + 1) * 10).quantize(
        Decimal("0.01")
    )


def parse_uk_tax_code(
    value,
    *,
    default_basis=BASIS_CUMULATIVE,
):
    """Parse and validate one UK PAYE tax code."""

    normalized = normalize_tax_code(value)

    core_with_region, basis = _split_basis(
        normalized,
        default_basis,
    )

    core_code, region = _split_region(
        core_with_region
    )

    if not core_code:
        raise UKTaxCodeError(
            f"Invalid UK tax code: {normalized!r}."
        )

    supported_special_codes = (
        SPECIAL_CODES_BY_REGION[region]
    )

    if core_code in supported_special_codes:
        return ParsedUKTaxCode(
            raw_code=str(value),
            normalized_code=normalized,
            core_code=core_code,
            region=region,
            basis=basis,
            kind=KIND_SPECIAL,
            code_number=None,
            suffix=None,
            annual_allowance=ZERO,
            annual_additional_pay=ZERO,
            special_code=core_code,
        )

    k_match = K_CODE_PATTERN.fullmatch(
        core_code
    )

    if k_match:
        code_number = int(
            k_match.group("number")
        )

        return ParsedUKTaxCode(
            raw_code=str(value),
            normalized_code=normalized,
            core_code=core_code,
            region=region,
            basis=basis,
            kind=KIND_K_CODE,
            code_number=code_number,
            suffix=None,
            annual_allowance=ZERO,
            annual_additional_pay=(
                _additional_pay_from_k_number(
                    code_number
                )
            ),
            special_code=None,
        )

    allowance_match = ALLOWANCE_PATTERN.fullmatch(
        core_code
    )

    if allowance_match:
        code_number = int(
            allowance_match.group("number")
        )
        suffix = allowance_match.group("suffix")

        return ParsedUKTaxCode(
            raw_code=str(value),
            normalized_code=normalized,
            core_code=core_code,
            region=region,
            basis=basis,
            kind=KIND_ALLOWANCE,
            code_number=code_number,
            suffix=suffix,
            annual_allowance=(
                _allowance_from_number(
                    code_number
                )
            ),
            annual_additional_pay=ZERO,
            special_code=None,
        )

    raise UKTaxCodeError(
        f"Unsupported UK tax code: {normalized!r}."
    )
