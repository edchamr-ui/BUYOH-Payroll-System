"""PostgreSQL integration tests for Botswana payroll processing."""

from calendar import monthrange
from datetime import date
from decimal import Decimal

import pytest

from app.models.audit_log import AuditLog
from app.models.department import Department
from app.models.employee import Employee
from app.models.payroll_period import PayrollPeriod
from app.models.payroll_record import PayrollRecord
from app.models.payroll_year import PayrollYear
from app.models.statutory_rule_set import StatutoryRuleSet
from app.models.tax_band import TaxBand
from app.models.user import User
from app.services.payroll_service import (
    InvalidPayrollStatusError,
    PayrollPersistenceError,
    PayrollService,
)


ZERO = Decimal("0.00")


def create_period(
    database,
    *,
    user_id,
    year,
    month,
    status="Draft",
    payment_date=None,
):
    """Create one monthly payroll period."""

    payroll_year = PayrollYear.query.filter_by(
        year=year,
    ).one_or_none()

    if payroll_year is None:
        payroll_year = PayrollYear(
            year=year,
            status=PayrollYear.STATUS_OPEN,
            opened_by_user_id=user_id,
        )
        database.session.add(payroll_year)
        database.session.flush()

    final_day = monthrange(year, month)[1]

    period = PayrollPeriod(
        payroll_year_id=payroll_year.id,
        month=month,
        year=year,
        start_date=date(year, month, 1),
        end_date=date(year, month, final_day),
        payment_date=(
            payment_date
            or date(year, month, final_day)
        ),
        status=status,
        created_by=user_id,
    )

    database.session.add(period)
    database.session.flush()

    return period


def create_historical_record(
    database,
    *,
    period_id,
    employee_id,
    user_id,
    basic_salary,
    regular_paye,
    irregular_paye=ZERO,
):
    """Persist one historical payroll record."""

    basic_salary = Decimal(basic_salary)
    regular_paye = Decimal(regular_paye)
    irregular_paye = Decimal(irregular_paye)
    paye = regular_paye + irregular_paye

    record = PayrollRecord(
        payroll_period_id=period_id,
        employee_id=employee_id,
        processed_by=user_id,
        basic_salary=basic_salary,
        overtime_amount=ZERO,
        allowances_total=ZERO,
        gross_pay=basic_salary,
        nssa=ZERO,
        employer_nssa=ZERO,
        paye=paye,
        regular_paye=regular_paye,
        irregular_paye=irregular_paye,
        aids_levy=ZERO,
        other_deductions_total=ZERO,
        total_deductions=paye,
        net_pay=basic_salary - paye,
        employer_cost=basic_salary,
        status="Draft",
    )

    database.session.add(record)
    database.session.flush()

    return record


@pytest.fixture
def botswana_setup(database):
    """Create Botswana statutory configuration and payroll entities."""

    user = User(
        username="botswana_admin",
        email="botswana.admin@example.com",
        password_hash="integration-test-only",
        first_name="Botswana",
        last_name="Administrator",
        role="Admin",
        is_active=True,
    )

    department = Department(
        name="Botswana Operations",
        is_active=True,
    )

    database.session.add_all([
        user,
        department,
    ])
    database.session.flush()

    employee = Employee(
        department_id=department.id,
        employee_number="BW-0001",
        first_name="Kabelo",
        last_name="Molefe",
        email="kabelo.molefe@example.com",
        job_title="Operations Officer",
        employment_date=date(2025, 7, 1),
        basic_salary=Decimal("18000.00"),
        tax_residency="Resident",
        employment_status="Active",
        is_active=True,
    )

    rule_set = StatutoryRuleSet(
        name="Botswana BURS PAYE 2025",
        currency="BWP",
        effective_from=date(2025, 7, 1),
        effective_to=date(2027, 6, 30),
        nssa_employee_rate=Decimal("0.000000"),
        nssa_employer_rate=Decimal("0.000000"),
        nssa_monthly_ceiling=ZERO,
        aids_levy_rate=Decimal("0.000000"),
        paye_enabled=True,
        is_active=True,
        source_engine_type="botswana",
        source_country_code="BW",
        imported_from_library=False,
    )

    bands = (
        ("0.00", "4000.00", "0.000000"),
        ("4000.00", "7000.00", "0.050000"),
        ("7000.00", "10000.00", "0.125000"),
        ("10000.00", "13000.00", "0.187500"),
        ("13000.00", "33333.33", "0.250000"),
        ("33333.33", None, "0.275000"),
    )

    for order, (lower, upper, rate) in enumerate(
        bands,
        start=1,
    ):
        rule_set.tax_bands.append(
            TaxBand(
                band_order=order,
                lower_limit=Decimal(lower),
                upper_limit=(
                    Decimal(upper)
                    if upper is not None
                    else None
                ),
                rate=Decimal(rate),
            )
        )

    database.session.add_all([
        employee,
        rule_set,
    ])
    database.session.commit()

    return {
        "user_id": user.id,
        "employee_id": employee.id,
        "rule_set_id": rule_set.id,
    }


def test_process_period_persists_botswana_paye_and_audit(
    database,
    botswana_setup,
):
    """Persist exact PAYE components, period state, and audit entry."""

    period = create_period(
        database,
        user_id=botswana_setup["user_id"],
        year=2025,
        month=8,
    )
    database.session.commit()

    period_id = period.id

    result = PayrollService.process_period(
        period=period,
        processed_by_user_id=botswana_setup["user_id"],
        currency="BWP",
    )

    assert result.created_count == 1
    assert result.skipped_count == 0
    assert result.currency == "BWP"
    assert result.calculation_date == date(2025, 8, 31)
    assert result.provisional_rule_used is False

    database.session.remove()

    record = PayrollRecord.query.filter_by(
        payroll_period_id=period_id,
        employee_id=botswana_setup["employee_id"],
    ).one()

    assert record.basic_salary == Decimal("18000.00")
    assert record.gross_pay == Decimal("18000.00")
    assert record.regular_paye == Decimal("2337.50")
    assert record.irregular_paye == Decimal("0.00")
    assert record.paye == Decimal("2337.50")
    assert record.total_deductions == Decimal("2337.50")
    assert record.net_pay == Decimal("15662.50")

    reloaded_period = database.session.get(
        PayrollPeriod,
        period_id,
    )

    assert reloaded_period.status == "Processed"

    audit = AuditLog.query.filter_by(
        action="Payroll Processed",
        entity_type="PayrollPeriod",
        entity_id=period_id,
    ).one()

    assert audit.user_id == botswana_setup["user_id"]
    assert "Created 1 payroll record(s)" in audit.description
    assert "Botswana BURS PAYE 2025" in audit.description


def test_botswana_ytd_uses_persisted_july_to_june_history(
    database,
    botswana_setup,
):
    """Load YTD taxable income and PAYE from persisted records."""

    user_id = botswana_setup["user_id"]
    employee_id = botswana_setup["employee_id"]

    june_2025 = create_period(
        database,
        user_id=user_id,
        year=2025,
        month=6,
    )
    july_2025 = create_period(
        database,
        user_id=user_id,
        year=2025,
        month=7,
    )
    may_2026 = create_period(
        database,
        user_id=user_id,
        year=2026,
        month=5,
    )

    create_historical_record(
        database,
        period_id=june_2025.id,
        employee_id=employee_id,
        user_id=user_id,
        basic_salary="99999.00",
        regular_paye="9999.00",
    )
    create_historical_record(
        database,
        period_id=july_2025.id,
        employee_id=employee_id,
        user_id=user_id,
        basic_salary="4500.00",
        regular_paye="25.00",
    )
    create_historical_record(
        database,
        period_id=may_2026.id,
        employee_id=employee_id,
        user_id=user_id,
        basic_salary="5000.00",
        regular_paye="50.00",
    )

    database.session.commit()
    database.session.remove()

    ytd = PayrollService._botswana_ytd_context(
        employee_id=employee_id,
        calculation_date=date(2026, 6, 30),
    )

    assert ytd == {
        "elapsed_payments": 2,
        "regular_taxable_income": Decimal("9500.00"),
        "regular_variable_income": Decimal("0.00"),
        "regular_paye": Decimal("75.00"),
    }


def test_botswana_ytd_resets_in_july(
    database,
    botswana_setup,
):
    """Exclude the previous July–June tax year after July reset."""

    user_id = botswana_setup["user_id"]
    employee_id = botswana_setup["employee_id"]

    june_2026 = create_period(
        database,
        user_id=user_id,
        year=2026,
        month=6,
    )

    create_historical_record(
        database,
        period_id=june_2026.id,
        employee_id=employee_id,
        user_id=user_id,
        basic_salary="18000.00",
        regular_paye="2337.50",
    )

    database.session.commit()
    database.session.remove()

    ytd = PayrollService._botswana_ytd_context(
        employee_id=employee_id,
        calculation_date=date(2026, 7, 31),
    )

    assert ytd == {
        "elapsed_payments": 0,
        "regular_taxable_income": Decimal("0.00"),
        "regular_variable_income": Decimal("0.00"),
        "regular_paye": Decimal("0.00"),
    }


def test_processed_period_rerun_is_rejected(
    database,
    botswana_setup,
):
    """Reject rerunning a period after its status becomes Processed."""

    period = create_period(
        database,
        user_id=botswana_setup["user_id"],
        year=2025,
        month=9,
    )
    database.session.commit()

    PayrollService.process_period(
        period=period,
        processed_by_user_id=botswana_setup["user_id"],
        currency="BWP",
    )

    record_count = PayrollRecord.query.filter_by(
        payroll_period_id=period.id,
    ).count()

    with pytest.raises(
        InvalidPayrollStatusError,
        match="Only draft payroll periods can be processed",
    ):
        PayrollService.process_period(
            period=period,
            processed_by_user_id=botswana_setup["user_id"],
            currency="BWP",
        )

    assert PayrollRecord.query.filter_by(
        payroll_period_id=period.id,
    ).count() == record_count


def test_duplicate_record_protection_preserves_existing_data(
    database,
    botswana_setup,
):
    """Skip an existing employee and roll back an empty processing run."""

    period = create_period(
        database,
        user_id=botswana_setup["user_id"],
        year=2025,
        month=10,
    )

    existing = create_historical_record(
        database,
        period_id=period.id,
        employee_id=botswana_setup["employee_id"],
        user_id=botswana_setup["user_id"],
        basic_salary="18000.00",
        regular_paye="2337.50",
    )

    database.session.commit()

    existing_id = existing.id
    period_id = period.id

    with pytest.raises(
        PayrollPersistenceError,
        match="No new payroll records were created",
    ):
        PayrollService.process_period(
            period=period,
            processed_by_user_id=botswana_setup["user_id"],
            currency="BWP",
        )

    database.session.remove()

    records = PayrollRecord.query.filter_by(
        payroll_period_id=period_id,
    ).all()

    assert [record.id for record in records] == [existing_id]
    assert records[0].paye == Decimal("2337.50")

    reloaded_period = database.session.get(
        PayrollPeriod,
        period_id,
    )
    assert reloaded_period.status == "Draft"

    assert AuditLog.query.filter_by(
        action="Payroll Processed",
        entity_type="PayrollPeriod",
        entity_id=period_id,
    ).count() == 0
