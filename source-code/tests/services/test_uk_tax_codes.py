"""Tests for UK PAYE tax-code parsing."""

from decimal import Decimal

import pytest

from app.services.statutory_engines.uk_tax_codes import (
    BASIS_CUMULATIVE,
    BASIS_W1_M1,
    KIND_ALLOWANCE,
    KIND_K_CODE,
    KIND_SPECIAL,
    REGION_ENGLAND_NI,
    REGION_SCOTLAND,
    REGION_WALES,
    UKTaxCodeError,
    parse_uk_tax_code,
)


def test_parses_standard_allowance_code():
    result = parse_uk_tax_code("1257L")

    assert result.normalized_code == "1257L"
    assert result.core_code == "1257L"
    assert result.region == REGION_ENGLAND_NI
    assert result.basis == BASIS_CUMULATIVE
    assert result.kind == KIND_ALLOWANCE
    assert result.code_number == 1257
    assert result.suffix == "L"
    assert result.annual_allowance == Decimal("12570.00")
    assert result.annual_additional_pay == Decimal("0.00")


def test_normalizes_lowercase_and_whitespace():
    result = parse_uk_tax_code(
        "  1257l   m1  "
    )

    assert result.normalized_code == "1257L M1"
    assert result.core_code == "1257L"
    assert result.basis == BASIS_W1_M1
    assert result.is_non_cumulative is True


@pytest.mark.parametrize(
    ("tax_code", "expected_region"),
    (
        ("S1257L", REGION_SCOTLAND),
        ("C1257L", REGION_WALES),
        ("1257L", REGION_ENGLAND_NI),
    ),
)
def test_parses_tax_region_prefix(
    tax_code,
    expected_region,
):
    result = parse_uk_tax_code(tax_code)

    assert result.region == expected_region


@pytest.mark.parametrize(
    "emergency_marker",
    (
        "W1",
        "M1",
        "X",
        "NONCUM",
    ),
)
def test_parses_emergency_basis(
    emergency_marker,
):
    result = parse_uk_tax_code(
        f"1257L {emergency_marker}"
    )

    assert result.basis == BASIS_W1_M1
    assert result.is_non_cumulative is True


def test_uses_profile_basis_when_code_has_no_marker():
    result = parse_uk_tax_code(
        "1257L",
        default_basis=BASIS_W1_M1,
    )

    assert result.basis == BASIS_W1_M1


def test_explicit_emergency_marker_overrides_default_basis():
    result = parse_uk_tax_code(
        "1257L M1",
        default_basis=BASIS_CUMULATIVE,
    )

    assert result.basis == BASIS_W1_M1


def test_parses_k_code():
    result = parse_uk_tax_code("K154")

    assert result.kind == KIND_K_CODE
    assert result.code_number == 154
    assert result.is_k_code is True
    assert result.annual_allowance == Decimal("0.00")
    assert (
        result.annual_additional_pay
        == Decimal("1550.00")
    )


@pytest.mark.parametrize(
    ("tax_code", "expected_region"),
    (
        ("SK154", REGION_SCOTLAND),
        ("CK154", REGION_WALES),
    ),
)
def test_parses_regional_k_code(
    tax_code,
    expected_region,
):
    result = parse_uk_tax_code(tax_code)

    assert result.kind == KIND_K_CODE
    assert result.region == expected_region
    assert (
        result.annual_additional_pay
        == Decimal("1550.00")
    )


@pytest.mark.parametrize(
    "tax_code",
    (
        "BR",
        "D0",
        "D1",
        "NT",
        "0T",
        "SBR",
        "SD0",
        "SD1",
        "SD2",
        "SD3",
        "SNT",
        "S0T",
        "CBR",
        "CD0",
        "CD1",
        "CNT",
        "C0T",
    ),
)
def test_parses_special_codes(tax_code):
    result = parse_uk_tax_code(tax_code)

    expected_core = (
        tax_code[1:]
        if tax_code.startswith(("S", "C"))
        else tax_code
    )

    assert result.kind == KIND_SPECIAL
    assert result.is_special is True
    assert result.special_code == expected_core
    assert result.annual_allowance == Decimal("0.00")
    assert result.annual_additional_pay == Decimal("0.00")


@pytest.mark.parametrize(
    "tax_code",
    (
        None,
        "",
        " ",
        "ABC",
        "1257",
        "L1257",
        "K",
        "D2",
        "D3",
        "CD2",
        "CD3",
        "1257L INVALID",
        "1257L M1 EXTRA",
    ),
)
def test_rejects_invalid_or_unsupported_codes(
    tax_code,
):
    with pytest.raises(UKTaxCodeError):
        parse_uk_tax_code(tax_code)


def test_rejects_invalid_default_basis():
    with pytest.raises(
        UKTaxCodeError,
        match="UK tax basis",
    ):
        parse_uk_tax_code(
            "1257L",
            default_basis="INVALID",
        )
