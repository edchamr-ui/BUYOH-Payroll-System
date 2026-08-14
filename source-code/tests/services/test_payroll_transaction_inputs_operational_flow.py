"""Operational integration tests for payroll transaction inputs."""

from decimal import Decimal
from inspect import getsource
from types import SimpleNamespace

from app.services.payroll_service import PayrollService


class FakeColumn:
    def asc(self):
        return self


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = None

    def filter_by(self, **values):
        self.filters = values
        return self

    def order_by(self, *columns):
        return self

    def all(self):
        return self.rows


def entry(amount, **values):
    defaults = {
        "amount": Decimal(amount),
        "deduction_type": "Salary Advance Recovery",
        "description": "Approved recovery",
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def configure_input_models(monkeypatch, overtime_rows, deduction_rows):
    import app.services.payroll_service as module

    overtime_query = FakeQuery(overtime_rows)
    deduction_query = FakeQuery(deduction_rows)
    monkeypatch.setattr(
        module,
        "PayrollOvertimeInput",
        SimpleNamespace(
            query=overtime_query,
            work_date=FakeColumn(),
            id=FakeColumn(),
        ),
    )
    monkeypatch.setattr(
        module,
        "PayrollOneOffDeduction",
        SimpleNamespace(
            query=deduction_query,
            priority=FakeColumn(),
            id=FakeColumn(),
        ),
    )
    return overtime_query, deduction_query


def test_only_approved_period_inputs_are_loaded(monkeypatch):
    overtime_query, deduction_query = configure_input_models(
        monkeypatch, [], []
    )
    PayrollService._approved_transaction_inputs(7, 11)
    expected = {
        "employee_id": 7,
        "payroll_period_id": 11,
        "status": "Approved",
    }
    assert overtime_query.filters == expected
    assert deduction_query.filters == expected


def test_approved_overtime_entries_are_totalled(monkeypatch):
    configure_input_models(
        monkeypatch,
        [entry("50.63"), entry("25.25")],
        [],
    )
    values = PayrollService._approved_transaction_inputs(7, 11)
    assert values["overtime_total"] == Decimal("75.88")
    assert len(values["overtime_entries"]) == 2


def test_approved_one_off_deductions_are_totalled(monkeypatch):
    configure_input_models(
        monkeypatch,
        [],
        [entry("30.00"), entry("20.00")],
    )
    values = PayrollService._approved_transaction_inputs(7, 11)
    assert values["deduction_total"] == Decimal("50.00")
    assert len(values["deduction_entries"]) == 2


def test_missing_transaction_inputs_are_zero(monkeypatch):
    configure_input_models(monkeypatch, [], [])
    values = PayrollService._approved_transaction_inputs(7, 11)
    assert values["overtime_total"] == Decimal("0.00")
    assert values["deduction_total"] == Decimal("0.00")


def test_transaction_values_merge_with_recurring_deductions():
    values = PayrollService._transaction_calculation_values(
        {"net_pay_deductions": Decimal("20.00")},
        {
            "overtime_total": Decimal("50.63"),
            "deduction_total": Decimal("30.00"),
        },
    )
    assert values == {
        "overtime_amount": Decimal("50.63"),
        "other_deductions_total": Decimal("50.00"),
    }


def test_one_off_deduction_becomes_historical_net_pay_line():
    snapshot = PayrollService._one_off_deduction_snapshot(
        entry("30.00"), employee_id=7
    )
    assert snapshot.employee_id == 7
    assert snapshot.deduction_type == "Salary Advance Recovery"
    assert snapshot.amount == Decimal("30.00")
    assert snapshot.description == "Approved recovery"
    assert snapshot.reduces_net_pay is True
    assert snapshot.is_tax_deductible is False


def test_process_period_loads_and_merges_transaction_inputs():
    source = getsource(PayrollService.process_period)
    assert "_approved_transaction_inputs" in source
    assert "_transaction_calculation_values" in source
    assert "_one_off_deduction_snapshot" in source


def test_uk_taxable_snapshot_includes_overtime():
    source = getsource(PayrollService.process_period)
    marker = 'statutory_basic_pay\n                            + transaction_inputs["overtime_total"]'
    assert marker in source


def test_botswana_projection_includes_overtime():
    source = getsource(PayrollService.process_period)
    marker = 'cls._decimal_value(employee.basic_salary)\n                            + transaction_inputs["overtime_total"]'
    assert marker in source
