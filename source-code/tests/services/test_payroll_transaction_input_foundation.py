"""Foundation tests for period-specific transaction inputs."""

from decimal import Decimal

import pytest

from app.models.payroll_one_off_deduction import PayrollOneOffDeduction
from app.models.payroll_overtime_input import PayrollOvertimeInput
from app.time_utils import legacy_utc_now


def test_overtime_amount_uses_hours_rate_and_multiplier():
    assert PayrollOvertimeInput.calculate_amount(
        "10", "3.375", "1.5"
    ) == Decimal("50.63")


def test_overtime_money_rounds_half_up():
    assert PayrollOvertimeInput.calculate_amount(
        "1", "10.005", "1"
    ) == Decimal("10.01")


@pytest.mark.parametrize(
    "values",
    (("0", "5", "1.5"), ("1", "-1", "1.5"), ("1", "5", "0")),
)
def test_invalid_overtime_values_are_rejected(values):
    with pytest.raises(ValueError):
        PayrollOvertimeInput.calculate_amount(*values)


def test_overtime_recalculate_preserves_snapshot_amount():
    entry = PayrollOvertimeInput(
        payroll_period_id=1,
        employee_id=2,
        category="Ordinary",
        hours=Decimal("10"),
        hourly_rate=Decimal("3.375"),
        multiplier=Decimal("1.5"),
        amount=Decimal("0"),
    )
    assert entry.recalculate() == Decimal("50.63")
    assert entry.amount == Decimal("50.63")


def test_one_off_deduction_is_money_rounded():
    assert PayrollOneOffDeduction.money("30.005") == Decimal("30.01")


@pytest.mark.parametrize("value", ("0", "-0.01"))
def test_one_off_deduction_must_be_positive(value):
    with pytest.raises(ValueError, match="greater than zero"):
        PayrollOneOffDeduction.money(value)


def test_transaction_models_use_python_314_safe_utc_defaults():
    overtime_default = PayrollOvertimeInput.__table__.c.created_at.default.arg
    deduction_default = (
        PayrollOneOffDeduction.__table__.c.created_at.default.arg
    )
    assert callable(overtime_default)
    assert callable(deduction_default)
    assert "legacy_utc_now" in overtime_default.__name__
    assert "legacy_utc_now" in deduction_default.__name__
    assert legacy_utc_now().tzinfo is None


def test_transaction_models_have_period_employee_indexes():
    overtime_indexes = {index.name for index in PayrollOvertimeInput.__table__.indexes}
    deduction_indexes = {index.name for index in PayrollOneOffDeduction.__table__.indexes}
    assert "ix_overtime_period_employee" in overtime_indexes
    assert "ix_one_off_deduction_period_employee" in deduction_indexes
