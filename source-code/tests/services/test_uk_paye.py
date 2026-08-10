"""Tests for HMRC-compatible UK monthly PAYE calculations."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.statutory_engines.uk_paye import (
    UKPayeCalculationError,
    calculate_monthly_paye,
    calculate_monthly_paye_from_profile,
)
from app.services.statutory_engines.uk_tax_codes import (
    BASIS_W1_M1,
    REGION_SCOTLAND,
)


REST_OF_UK_CUMULATIVE = (
    ("1156.25", "1257L", 1, "21.40", "21.40"),
    ("1156.26", "1257L", 2, "21.60", "43.00"),
    ("31123.26", "1257L", 3, "10188.00", "10231.00"),
    ("14465.71", "1257L", 4, "4838.60", "15069.60"),
    ("52681.25", "1257L", 5, "22085.10", "37154.70"),
    ("50000.00", "1257L", 6, "20878.65", "58033.35"),
    ("15000.00", "1257L", 7, "5128.20", "63161.55"),
    ("14000.55", "1257L", 8, "4679.10", "67840.65"),
    ("12590.45", "BR", 9, "-29406.05", "38434.60"),
    ("11245.05", "NT", 10, "-38434.60", "0.00"),
)

SCOTTISH_CUMULATIVE = (
    ("1156.25", "S1257L", 1, "20.33", "20.33"),
    ("1156.26", "S1257L", 2, "20.52", "40.85"),
    ("31123.26", "S1257L", 3, "11436.78", "11477.63"),
    ("14465.71", "S1257L", 4, "5380.32", "16857.95"),
    ("52681.25", "S1257L", 5, "23753.37", "40611.32"),
    ("50000.00", "S1257L", 6, "22466.49", "63077.81"),
    ("15000.00", "S1257L", 7, "5666.01", "68743.82"),
    ("14000.55", "S1257L", 8, "5186.97", "73930.79"),
    ("12590.45", "SBR", 9, "-35496.19", "38434.60"),
    ("11245.05", "NT", 10, "-38434.60", "0.00"),
)

WELSH_CUMULATIVE = tuple(
    (pay, f"C{code}" if code != "NT" else code, month, due, total)
    for pay, code, month, due, total in REST_OF_UK_CUMULATIVE
)


@pytest.mark.parametrize(
    "official_rows",
    (REST_OF_UK_CUMULATIVE, SCOTTISH_CUMULATIVE, WELSH_CUMULATIVE),
)
def test_official_hmrc_cumulative_monthly_vectors(official_rows):
    """Reproduce HMRC's sequential 2026/27 monthly examples."""

    prior_pay = Decimal("0.00")
    prior_tax = Decimal("0.00")

    for pay, code, month, expected_due, expected_total in official_rows:
        result = calculate_monthly_paye(
            tax_code=code,
            current_taxable_pay=pay,
            tax_month=month,
            prior_taxable_pay=prior_pay,
            prior_tax_paid=prior_tax,
        )

        assert result.paye == Decimal(expected_due)
        assert result.tax_paid_to_date == Decimal(expected_total)

        prior_pay += Decimal(pay)
        prior_tax = result.tax_paid_to_date


@pytest.mark.parametrize(
    ("tax_code", "pay", "expected_paye"),
    (
        ("45L", "39.24", "0.00"),
        ("45L", "39.25", "0.20"),
        ("45L", "3164.24", "625.00"),
        ("45L", "3164.25", "625.20"),
        ("45L", "10450.24", "3536.06"),
        ("45L", "10500.78", "3558.15"),
        ("45L", "12539.24", "4475.25"),
        ("45L", "12539.25", "4475.70"),
        ("BR", "99.99", "19.80"),
        ("D0", "99.99", "39.60"),
        ("D1", "99.99", "44.55"),
        ("C45L", "3164.25", "625.20"),
        ("CBR", "99.99", "19.80"),
        ("CD0", "99.99", "39.60"),
        ("CD1", "99.99", "44.55"),
        ("S45L", "39.25", "0.19"),
        ("S45L", "3164.24", "750.95"),
        ("S45L", "3164.25", "751.37"),
        ("S45L", "10450.24", "3967.32"),
        ("S45L", "10500.78", "3991.28"),
        ("S45L", "12539.24", "4969.52"),
        ("S45L", "12539.25", "4970.00"),
        ("SBR", "99.99", "19.80"),
        ("SD0", "99.99", "20.79"),
        ("SD1", "99.99", "41.58"),
        ("SD2", "99.99", "44.55"),
        ("SD3", "99.99", "47.52"),
    ),
)
def test_official_hmrc_month_one_vectors(tax_code, pay, expected_paye):
    result = calculate_monthly_paye(
        tax_code=tax_code,
        current_taxable_pay=pay,
        tax_month=1,
        default_basis=BASIS_W1_M1,
    )

    assert result.paye == Decimal(expected_paye)


@pytest.mark.parametrize(
    ("tax_code", "pay", "expected_paye"),
    (
        ("999L", "2500", "333.20"),
        ("1000L", "3000", "433.00"),
        ("1001L", "5000", "1037.66"),
        ("K45", "950", "197.60"),
        ("K285", "1120", "271.60"),
        ("K401", "885", "243.80"),
    ),
)
def test_official_large_and_month_one_k_code_vectors(
    tax_code,
    pay,
    expected_paye,
):
    basis = BASIS_W1_M1 if tax_code.startswith("K") else "CUMULATIVE"
    result = calculate_monthly_paye(
        tax_code=tax_code,
        current_taxable_pay=pay,
        tax_month=1,
        default_basis=basis,
    )

    assert result.paye == Decimal(expected_paye)


@pytest.mark.parametrize(
    ("tax_code", "rows"),
    (
        (
            "K585",
            (
                ("895", 1, "276.60", "276.60"),
                ("1250", 2, "347.60", "624.20"),
                ("765", 3, "250.60", "874.80"),
            ),
        ),
        (
            "SK585",
            (
                ("895", 1, "273.29", "273.29"),
                ("1250", 2, "347.24", "620.53"),
                ("765", 3, "245.70", "866.23"),
            ),
        ),
    ),
)
def test_official_hmrc_cumulative_k_code_vectors(tax_code, rows):
    prior_pay = Decimal("0.00")
    prior_tax = Decimal("0.00")

    for pay, month, expected_due, expected_total in rows:
        result = calculate_monthly_paye(
            tax_code=tax_code,
            current_taxable_pay=pay,
            tax_month=month,
            prior_taxable_pay=prior_pay,
            prior_tax_paid=prior_tax,
        )

        assert result.paye == Decimal(expected_due)
        assert result.tax_paid_to_date == Decimal(expected_total)

        prior_pay += Decimal(pay)
        prior_tax = result.tax_paid_to_date


def test_regulatory_limit_caps_deduction_at_fifty_percent():
    result = calculate_monthly_paye(
        tax_code="K9999",
        current_taxable_pay="100",
        current_pay_for_regulatory_limit="100",
        tax_month=1,
    )

    assert result.paye_before_regulatory_limit > Decimal("50.00")
    assert result.regulatory_limit == Decimal("50.00")
    assert result.regulatory_limit_applied is True
    assert result.paye == Decimal("50.00")


def test_regulatory_limit_excludes_payrolled_benefits():
    result = calculate_monthly_paye(
        tax_code="K9999",
        current_taxable_pay="1000",
        current_pay_for_regulatory_limit="1000",
        payrolled_benefits="200",
        tax_month=1,
    )

    assert result.regulatory_limit == Decimal("400.00")
    assert result.paye == Decimal("400.00")


def test_cumulative_nt_refunds_prior_tax():
    result = calculate_monthly_paye(
        tax_code="NT",
        current_taxable_pay="3000",
        prior_taxable_pay="3000",
        prior_tax_paid="400",
        tax_month=2,
    )

    assert result.is_refund is True
    assert result.paye == Decimal("-400.00")
    assert result.tax_paid_to_date == Decimal("0.00")


def test_profile_calculation_uses_profile_fields():
    profile = SimpleNamespace(
        tax_code="S1257L",
        tax_basis="CUMULATIVE",
        tax_region="SCOTLAND",
    )

    result = calculate_monthly_paye_from_profile(
        tax_profile=profile,
        current_taxable_pay="4000",
        tax_month=1,
    )

    assert result.tax_region == REGION_SCOTLAND
    assert result.paye == Decimal("677.87")

def test_profile_rejects_region_mismatch():
    profile = SimpleNamespace(
        tax_code="S1257L",
        tax_basis="CUMULATIVE",
        tax_region="WALES",
    )

    with pytest.raises(UKPayeCalculationError, match="does not match"):
        calculate_monthly_paye_from_profile(
            tax_profile=profile,
            current_taxable_pay="4000",
            tax_month=1,
        )


@pytest.mark.parametrize("tax_month", (0, 13, "invalid", None, 1.5))
def test_rejects_invalid_tax_month(tax_month):
    with pytest.raises(UKPayeCalculationError, match="tax month"):
        calculate_monthly_paye(
            tax_code="1257L",
            current_taxable_pay="4000",
            tax_month=tax_month,
        )


@pytest.mark.parametrize(
    ("message", "arguments"),
    (
        ("Current taxable pay", {"current_taxable_pay": "-1"}),
        (
            "Prior taxable pay",
            {"current_taxable_pay": "100", "prior_taxable_pay": "-1"},
        ),
        (
            "Current pay for regulatory limit",
            {
                "current_taxable_pay": "100",
                "current_pay_for_regulatory_limit": "-1",
            },
        ),
        (
            "Payrolled benefits",
            {"current_taxable_pay": "100", "payrolled_benefits": "-1"},
        ),
    ),
)
def test_rejects_negative_non_refund_inputs(message, arguments):
    with pytest.raises(UKPayeCalculationError, match=message):
        calculate_monthly_paye(
            tax_code="1257L",
            tax_month=1,
            **arguments,
        )


def test_rejects_benefits_above_regulatory_limit_pay():
    with pytest.raises(
        UKPayeCalculationError,
        match="Payrolled benefits cannot exceed",
    ):
        calculate_monthly_paye(
            tax_code="1257L",
            current_taxable_pay="100",
            current_pay_for_regulatory_limit="100",
            payrolled_benefits="101",
            tax_month=1,
        )


def test_requires_profile():
    with pytest.raises(UKPayeCalculationError, match="profile is required"):
        calculate_monthly_paye_from_profile(
            tax_profile=None,
            current_taxable_pay="1000",
            tax_month=1,
        )
