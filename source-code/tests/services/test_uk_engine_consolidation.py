"""Cross-module assurance tests for the complete UK 2026/27 engine."""

from datetime import date, timedelta
from decimal import Decimal
from inspect import signature
from types import SimpleNamespace

import pytest

from app.services.statutory_engines.registry import StatutoryEngineRegistry
from app.services.statutory_engines.uk import UKStatutoryEngine


RATE_DATE = date(2026, 4, 5)


def uk_config():
    return SimpleNamespace(currency="GBP", paye_enabled=True, tax_bands=())


def uk_profile(**overrides):
    values = {
        "tax_code": "1257L",
        "tax_basis": "CUMULATIVE",
        "tax_region": "ENGLAND_NI",
        "ni_category": "A",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_registry_exposes_one_engine_for_every_supported_uk_alias():
    engines = [
        StatutoryEngineRegistry.resolve(key)
        for key in ("UK_PAYE", "UK", "GB", "GBR", "GB_PAYE")
    ]

    assert all(isinstance(engine, UKStatutoryEngine) for engine in engines)
    assert {engine.engine_key for engine in engines} == {"UK_PAYE"}


def test_complete_engine_exposes_every_statutory_pay_contract():
    expected_parameters = {
        "calculate_statutory_sick_pay": {
            "average_weekly_earnings",
            "qualifying_days_per_week",
            "qualifying_days_sick",
            "prior_paid_qualifying_days",
        },
        "calculate_statutory_maternity_pay": {
            "average_weekly_earnings",
            "paid_days",
            "prior_paid_days",
        },
        "calculate_statutory_paternity_pay": {
            "average_weekly_earnings",
            "paid_days",
            "prior_paid_days",
        },
        "calculate_statutory_adoption_pay": {
            "average_weekly_earnings",
            "paid_days",
            "prior_paid_days",
        },
        "calculate_statutory_shared_parental_pay": {
            "average_weekly_earnings",
            "allocated_days",
            "paid_days",
            "prior_paid_days",
        },
        "calculate_statutory_parental_bereavement_pay": {
            "average_weekly_earnings",
            "paid_days",
            "prior_paid_days",
        },
        "calculate_statutory_neonatal_care_pay": {
            "average_weekly_earnings",
            "accrued_weeks",
            "paid_days",
            "prior_paid_days",
        },
    }

    for method_name, required in expected_parameters.items():
        parameters = set(signature(getattr(UKStatutoryEngine, method_name)).parameters)
        assert required <= parameters


def test_integrated_paye_ni_and_payroll_totals_reconcile():
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
    assert result.nssa == Decimal("244.16")
    assert result.employer_nssa == Decimal("552.45")
    assert result.total_deductions == Decimal("884.36")
    assert result.net_pay == result.gross_pay - result.total_deductions
    assert result.employer_cost == result.gross_pay + result.employer_nssa


def test_ssp_uses_the_2026_27_weekly_rate_through_the_engine():
    result = UKStatutoryEngine().calculate_statutory_sick_pay(
        average_weekly_earnings="500",
        qualifying_days_per_week=5,
        qualifying_days_sick=5,
        statutory_config=uk_config(),
    )

    assert result.tax_year == "2026/27"
    assert result.weekly_rate == Decimal("123.25")
    assert result.amount == Decimal("123.25")


@pytest.mark.parametrize(
    ("method_name", "extra"),
    (
        ("calculate_statutory_paternity_pay", {}),
        ("calculate_statutory_shared_parental_pay", {"allocated_days": 7}),
        ("calculate_statutory_parental_bereavement_pay", {}),
        ("calculate_statutory_neonatal_care_pay", {"accrued_weeks": 1}),
    ),
)
def test_flat_rate_family_payments_share_the_confirmed_weekly_cap(
    method_name,
    extra,
):
    result = getattr(UKStatutoryEngine(), method_name)(
        average_weekly_earnings="500",
        paid_days=7,
        payment_date=RATE_DATE,
        statutory_config=uk_config(),
        **extra,
    )

    assert result.rate_year == "2026/27"
    assert result.weekly_rate == Decimal("194.32")
    assert result.amount == Decimal("194.32")


@pytest.mark.parametrize(
    "method_name",
    (
        "calculate_statutory_maternity_pay",
        "calculate_statutory_adoption_pay",
    ),
)
def test_smp_and_sap_preserve_the_uncapped_first_six_week_rate(method_name):
    result = getattr(UKStatutoryEngine(), method_name)(
        average_weekly_earnings="1000",
        paid_days=7,
        payment_date=RATE_DATE,
        statutory_config=uk_config(),
    )

    assert result.higher_weekly_rate == Decimal("900.00")
    assert result.amount == Decimal("900.00")


def test_every_family_payment_uses_the_inclusive_129_pound_lel():
    engine = UKStatutoryEngine()
    calls = (
        (engine.calculate_statutory_maternity_pay, {}),
        (engine.calculate_statutory_paternity_pay, {}),
        (engine.calculate_statutory_adoption_pay, {}),
        (engine.calculate_statutory_shared_parental_pay, {"allocated_days": 7}),
        (engine.calculate_statutory_parental_bereavement_pay, {}),
        (engine.calculate_statutory_neonatal_care_pay, {"accrued_weeks": 1}),
    )

    for method, extra in calls:
        result = method(
            average_weekly_earnings="129",
            paid_days=7,
            payment_date=RATE_DATE,
            statutory_config=uk_config(),
            **extra,
        )
        assert result.eligible_by_earnings is True
        assert result.amount == Decimal("116.10")


def test_family_payment_rate_year_is_5_april_to_4_april():
    engine = UKStatutoryEngine()
    for payment_date in (date(2026, 4, 5), date(2027, 4, 4)):
        result = engine.calculate_statutory_paternity_pay(
            average_weekly_earnings="500",
            paid_days=7,
            payment_date=payment_date,
            statutory_config=uk_config(),
        )
        assert result.rate_year == "2026/27"


def test_tax_year_dates_cover_exactly_twelve_calendar_months():
    start = date(2026, 4, 5)
    end = date(2027, 4, 4)

    assert end == start + timedelta(days=364)
