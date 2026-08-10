"""Tests for the UK statutory-engine wrapper and registry."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.statutory_engines.base import (
    InvalidStatutoryConfigurationError,
)
from app.services.statutory_engines.registry import (
    StatutoryEngineRegistry,
)
from app.services.statutory_engines.uk import UKStatutoryEngine


def uk_config(**overrides):
    values = {
        "currency": "GBP",
        "paye_enabled": True,
        "tax_bands": (),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def uk_profile(**overrides):
    values = {
        "tax_code": "1257L",
        "tax_basis": "CUMULATIVE",
        "tax_region": "ENGLAND_NI",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_validates_uk_configuration_without_database_tax_bands():
    validation = UKStatutoryEngine.validate_configuration(uk_config())

    assert validation.valid is True
    assert validation.errors == ()


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"currency": "USD"}, "requires GBP"),
        ({"paye_enabled": False}, "must be enabled"),
    ),
)
def test_rejects_invalid_uk_configuration(overrides, message):
    validation = UKStatutoryEngine.validate_configuration(
        uk_config(**overrides)
    )

    assert validation.valid is False
    assert any(message in error for error in validation.errors)


def test_warns_that_generic_tax_bands_are_ignored():
    validation = UKStatutoryEngine.validate_configuration(
        uk_config(tax_bands=(object(),))
    )

    assert validation.valid is True
    assert "ignored" in validation.warnings[0]


def test_calculate_paye_returns_auditable_hmrc_result():
    result = UKStatutoryEngine().calculate_paye(
        taxable_income="4000",
        statutory_config=uk_config(),
        tax_profile=uk_profile(),
        tax_month=1,
    )

    assert result.paye == Decimal("590.20")
    assert result.tax_paid_to_date == Decimal("590.20")
    assert result.tax_code == "1257L"


def test_calculate_returns_backward_compatible_payroll_result():
    result = UKStatutoryEngine().calculate(
        basic_salary="3500",
        overtime_amount="200",
        allowances_total="400",
        taxable_allowances_total="300",
        non_cash_benefits_total="100",
        allowable_deductions_total="100",
        other_deductions_total="50",
        statutory_config=uk_config(),
        tax_profile=uk_profile(),
        tax_month=1,
    )

    assert result.gross_pay == Decimal("4100.00")
    assert result.paye == Decimal("590.20")
    assert result.nssa == Decimal("0.00")
    assert result.employer_nssa == Decimal("0.00")
    assert result.aids_levy == Decimal("0.00")
    assert result.total_deductions == Decimal("640.20")
    assert result.net_pay == Decimal("3459.80")
    assert result.employer_cost == Decimal("4100.00")


def test_calculate_supports_cumulative_history_and_refunds():
    result = UKStatutoryEngine().calculate(
        basic_salary="11245.05",
        overtime_amount=0,
        allowances_total=0,
        other_deductions_total=0,
        statutory_config=uk_config(),
        tax_profile=uk_profile(tax_code="NT"),
        tax_month=10,
        prior_taxable_pay="136017.53",
        prior_tax_paid="38434.60",
    )

    assert result.paye == Decimal("-38434.60")
    assert result.total_deductions == Decimal("-38434.60")
    assert result.net_pay == Decimal("49679.65")


def test_calculate_rejects_invalid_configuration():
    with pytest.raises(
        InvalidStatutoryConfigurationError,
        match="requires GBP",
    ):
        UKStatutoryEngine().calculate(
            basic_salary="1000",
            overtime_amount=0,
            allowances_total=0,
            other_deductions_total=0,
            statutory_config=uk_config(currency="USD"),
            tax_profile=uk_profile(),
            tax_month=1,
        )


@pytest.mark.parametrize(
    "engine_key",
    ("UK_PAYE", "UK", "GB", "GBR", "GB_PAYE"),
)
def test_registry_resolves_every_uk_engine_key(engine_key):
    engine = StatutoryEngineRegistry.resolve(engine_key)

    assert isinstance(engine, UKStatutoryEngine)


@pytest.mark.parametrize(
    "rule_set",
    (
        SimpleNamespace(
            source_engine_type="UK_PAYE",
            source_country_code=None,
            currency="GBP",
        ),
        SimpleNamespace(
            source_engine_type=None,
            source_country_code="GB",
            currency="GBP",
        ),
        SimpleNamespace(
            source_engine_type=None,
            source_country_code="UK",
            currency="GBP",
        ),
        SimpleNamespace(
            source_engine_type=None,
            source_country_code=None,
            currency="GBP",
        ),
    ),
)
def test_registry_resolves_uk_rule_sets(rule_set):
    engine = StatutoryEngineRegistry.resolve_for_rule_set(rule_set)

    assert isinstance(engine, UKStatutoryEngine)


def test_registry_reports_uk_keys_as_registered():
    registered = StatutoryEngineRegistry.registered_keys()

    assert "UK_PAYE" in registered
    assert "GB" in registered
    assert "GBP" not in registered
