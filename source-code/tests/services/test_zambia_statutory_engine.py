"""Automated tests for the Zambia statutory payroll engine."""

from decimal import Decimal

import pytest

from app.services.statutory_config import (
    StatutoryConfiguration,
    TaxBandConfiguration,
)
from app.services.statutory_engines.zambia import (
    ZambiaStatutoryEngine,
)


ZERO = Decimal("0.00")


@pytest.fixture
def zambia_config():
    return StatutoryConfiguration(
        currency="ZMW",
        nssa_employee_rate=Decimal("0.050000"),
        nssa_employer_rate=Decimal("0.050000"),
        nssa_monthly_ceiling=Decimal("28920.30"),
        aids_levy_rate=Decimal("0.000000"),
        paye_enabled=True,
        tax_bands=(
            TaxBandConfiguration(1, Decimal("0.00"), Decimal("5100.00"), Decimal("0.000000")),
            TaxBandConfiguration(2, Decimal("5100.00"), Decimal("7100.00"), Decimal("0.200000")),
            TaxBandConfiguration(3, Decimal("7100.00"), Decimal("9200.00"), Decimal("0.300000")),
            TaxBandConfiguration(4, Decimal("9200.00"), None, Decimal("0.370000")),
        ),
    )


def calculate(engine, config, salary):
    return engine.calculate(
        basic_salary=Decimal(str(salary)),
        overtime_amount=ZERO,
        allowances_total=ZERO,
        other_deductions_total=ZERO,
        statutory_config=config,
    )


def test_zambia_configuration_is_valid(zambia_config):
    validation = ZambiaStatutoryEngine.validate_configuration(
        zambia_config
    )

    assert validation.valid is True
    assert validation.errors == ()


@pytest.mark.parametrize(
    (
        "gross_salary",
        "expected_napsa",
        "expected_paye",
        "expected_net",
    ),
    [
        ("0.00", "0.00", "0.00", "0.00"),
        ("5100.00", "255.00", "0.00", "4845.00"),
        ("7100.00", "355.00", "329.00", "6416.00"),
        ("9200.00", "460.00", "889.00", "7851.00"),
        ("10000.00", "500.00", "1141.00", "8359.00"),
    ],
)
def test_zambia_salary_examples(
    zambia_config,
    gross_salary,
    expected_napsa,
    expected_paye,
    expected_net,
):
    result = calculate(
        ZambiaStatutoryEngine(),
        zambia_config,
        gross_salary,
    )

    assert result.nssa == Decimal(expected_napsa)
    assert result.employer_nssa == Decimal(expected_napsa)
    assert result.paye == Decimal(expected_paye)
    assert result.aids_levy == ZERO
    assert result.net_pay == Decimal(expected_net)


def test_napsa_is_capped_above_ceiling(zambia_config):
    result = calculate(
        ZambiaStatutoryEngine(),
        zambia_config,
        "50000.00",
    )

    assert result.nssa == Decimal("1446.02")
    assert result.employer_nssa == Decimal("1446.02")


def test_employer_cost_includes_employer_napsa(zambia_config):
    result = calculate(
        ZambiaStatutoryEngine(),
        zambia_config,
        "10000.00",
    )

    assert result.employer_cost == Decimal("10500.00")


def test_other_deductions_reduce_net_pay(zambia_config):
    result = ZambiaStatutoryEngine().calculate(
        basic_salary=Decimal("10000.00"),
        overtime_amount=ZERO,
        allowances_total=ZERO,
        other_deductions_total=Decimal("200.00"),
        statutory_config=zambia_config,
    )

    assert result.total_deductions == Decimal("1841.00")
    assert result.net_pay == Decimal("8159.00")


def test_negative_salary_is_rejected(zambia_config):
    with pytest.raises(
        ValueError,
        match="Basic salary cannot be negative",
    ):
        calculate(
            ZambiaStatutoryEngine(),
            zambia_config,
            "-1.00",
        )


def test_wrong_currency_is_rejected(zambia_config):
    invalid = StatutoryConfiguration(
        currency="USD",
        nssa_employee_rate=zambia_config.nssa_employee_rate,
        nssa_employer_rate=zambia_config.nssa_employer_rate,
        nssa_monthly_ceiling=zambia_config.nssa_monthly_ceiling,
        aids_levy_rate=zambia_config.aids_levy_rate,
        paye_enabled=zambia_config.paye_enabled,
        tax_bands=zambia_config.tax_bands,
    )

    validation = ZambiaStatutoryEngine.validate_configuration(
        invalid
    )

    assert validation.valid is False
    assert "The Zambia engine requires ZMW currency." in validation.errors
