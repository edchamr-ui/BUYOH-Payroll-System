"""Production-flow integration tests for Botswana payroll."""

from datetime import date
from decimal import Decimal

from app.models.allowance import Allowance
from app.models.allowance_type import AllowanceType
from app.models.audit_log import AuditLog
from app.models.deduction import Deduction
from app.models.deduction_type import DeductionType
from app.models.employee import Employee
from app.models.employee_allowance import EmployeeAllowance
from app.models.employee_deduction import EmployeeDeduction
from app.models.payroll_period import PayrollPeriod
from app.models.payroll_record import PayrollRecord
from app.models.statutory_rule_set import StatutoryRuleSet
from app.services.payroll_service import PayrollService
from tests.services.test_botswana_payroll_integration import (
    botswana_setup,
    create_period,
)


ZERO = Decimal("0.00")


def add_employee(
    database,
    *,
    department_id,
    number,
    first_name,
    basic_salary,
    residency,
):
    """Create an active Botswana employee."""

    employee = Employee(
        department_id=department_id,
        employee_number=number,
        first_name=first_name,
        last_name="Integration",
        email=f"{number.lower()}@example.com",
        job_title="Test Employee",
        employment_date=date(2025, 7, 1),
        basic_salary=Decimal(basic_salary),
        tax_residency=residency,
        employment_status="Active",
        is_active=True,
    )

    database.session.add(employee)
    database.session.flush()

    return employee


def add_allowance(
    database,
    *,
    employee,
    user_id,
    name,
    code,
    amount,
    classification,
    taxable=True,
    start_date=None,
    end_date=None,
    active=True,
):
    """Assign a fixed recurring allowance."""

    definition = AllowanceType(
        name=name,
        code=code,
        calculation_method=AllowanceType.CALCULATION_FIXED,
        default_amount=ZERO,
        default_percentage=ZERO,
        is_taxable=taxable,
        earning_classification=classification,
        is_recurring=True,
        is_active=True,
        created_by=user_id,
    )

    assignment = EmployeeAllowance(
        employee=employee,
        allowance_type=definition,
        amount=Decimal(amount),
        percentage=ZERO,
        start_date=start_date,
        end_date=end_date,
        is_active=active,
        created_by=user_id,
    )

    database.session.add_all([
        definition,
        assignment,
    ])

    return assignment


def add_deduction(
    database,
    *,
    employee,
    user_id,
    name,
    code,
    amount,
    tax_deductible,
    reduces_net_pay=True,
):
    """Assign a fixed recurring deduction."""

    definition = DeductionType(
        name=name,
        code=code,
        category=DeductionType.CATEGORY_VOLUNTARY,
        calculation_method=DeductionType.CALCULATION_FIXED,
        default_amount=ZERO,
        default_percentage=ZERO,
        employer_percentage=ZERO,
        is_statutory=False,
        reduces_net_pay=reduces_net_pay,
        is_tax_deductible=tax_deductible,
        is_recurring=True,
        is_active=True,
        created_by=user_id,
    )

    assignment = EmployeeDeduction(
        employee=employee,
        deduction_type=definition,
        amount=Decimal(amount),
        percentage=ZERO,
        employer_amount=ZERO,
        employer_percentage=ZERO,
        is_active=True,
        created_by=user_id,
    )

    database.session.add_all([
        definition,
        assignment,
    ])

    return assignment


def test_processes_multiple_employees_and_recurring_components(
    database,
    botswana_setup,
):
    """
    Process resident, non-resident, commission, bonus, and
    tax-deductible recurring components in one payroll run.
    """

    user_id = botswana_setup["user_id"]

    resident = database.session.get(
        Employee,
        botswana_setup["employee_id"],
    )
    department_id = resident.department_id

    non_resident = add_employee(
        database,
        department_id=department_id,
        number="BW-0002",
        first_name="Naledi",
        basic_salary="7000.00",
        residency="Non-Resident",
    )

    bonus_employee = add_employee(
        database,
        department_id=department_id,
        number="BW-0003",
        first_name="Thato",
        basic_salary="4000.00",
        residency="Resident",
    )

    add_allowance(
        database,
        employee=resident,
        user_id=user_id,
        name="Sales Commission",
        code="BW-COMMISSION",
        amount="700.00",
        classification=AllowanceType.EARNING_COMMISSION,
    )

    add_deduction(
        database,
        employee=resident,
        user_id=user_id,
        name="Approved Pension",
        code="BW-PENSION",
        amount="200.00",
        tax_deductible=True,
    )

    add_allowance(
        database,
        employee=bonus_employee,
        user_id=user_id,
        name="Annual Performance Bonus",
        code="BW-BONUS",
        amount="4000.00",
        classification=AllowanceType.EARNING_BONUS,
    )

    period = create_period(
        database,
        user_id=user_id,
        year=2025,
        month=11,
    )

    database.session.commit()

    period_id = period.id
    resident_id = resident.id
    non_resident_id = non_resident.id
    bonus_employee_id = bonus_employee.id

    result = PayrollService.process_period(
        period=period,
        processed_by_user_id=user_id,
        currency="BWP",
    )

    assert result.created_count == 3
    assert result.skipped_count == 0
    assert result.currency == "BWP"
    assert result.provisional_rule_used is False

    database.session.remove()

    records = {
        record.employee_id: record
        for record in PayrollRecord.query.filter_by(
            payroll_period_id=period_id,
        ).all()
    }

    assert set(records) == {
        resident_id,
        non_resident_id,
        bonus_employee_id,
    }

    resident_record = records[resident_id]

    assert resident_record.basic_salary == Decimal("18000.00")
    assert resident_record.allowances_total == Decimal("700.00")
    assert resident_record.gross_pay == Decimal("18700.00")
    assert resident_record.regular_paye == Decimal("2462.50")
    assert resident_record.irregular_paye == ZERO
    assert resident_record.paye == Decimal("2462.50")
    assert resident_record.other_deductions_total == Decimal("200.00")
    assert resident_record.total_deductions == Decimal("2662.50")
    assert resident_record.net_pay == Decimal("16037.50")
    assert resident_record.nssa == ZERO
    assert resident_record.employer_nssa == ZERO
    assert resident_record.aids_levy == ZERO
    assert resident_record.employer_cost == Decimal("18700.00")

    commission = Allowance.query.filter_by(
        payroll_record_id=resident_record.id,
        allowance_type="Sales Commission",
    ).one()

    assert commission.amount == Decimal("700.00")
    assert commission.earning_classification == "Commission"
    assert commission.is_taxable is True

    pension = Deduction.query.filter_by(
        payroll_record_id=resident_record.id,
        deduction_type="Approved Pension",
    ).one()

    assert pension.amount == Decimal("200.00")
    assert pension.is_tax_deductible is True
    assert pension.reduces_net_pay is True

    non_resident_record = records[non_resident_id]

    assert non_resident_record.gross_pay == Decimal("7000.00")
    assert non_resident_record.regular_paye == Decimal("350.00")
    assert non_resident_record.irregular_paye == ZERO
    assert non_resident_record.net_pay == Decimal("6650.00")

    bonus_record = records[bonus_employee_id]

    assert bonus_record.gross_pay == Decimal("8000.00")
    assert bonus_record.regular_paye == ZERO
    assert bonus_record.irregular_paye == Decimal("200.00")
    assert bonus_record.paye == Decimal("200.00")
    assert bonus_record.net_pay == Decimal("7800.00")

    bonus = Allowance.query.filter_by(
        payroll_record_id=bonus_record.id,
        allowance_type="Annual Performance Bonus",
    ).one()

    assert bonus.amount == Decimal("4000.00")
    assert bonus.earning_classification == "Bonus"


def test_excludes_inactive_and_out_of_date_assignments(
    database,
    botswana_setup,
):
    """Ignore assignments that are inactive or outside their dates."""

    user_id = botswana_setup["user_id"]
    employee = database.session.get(
        Employee,
        botswana_setup["employee_id"],
    )

    add_allowance(
        database,
        employee=employee,
        user_id=user_id,
        name="Expired Allowance",
        code="BW-EXPIRED",
        amount="900.00",
        classification=AllowanceType.EARNING_REGULAR,
        end_date=date(2025, 9, 30),
    )

    add_allowance(
        database,
        employee=employee,
        user_id=user_id,
        name="Inactive Allowance",
        code="BW-INACTIVE",
        amount="800.00",
        classification=AllowanceType.EARNING_REGULAR,
        active=False,
    )

    add_allowance(
        database,
        employee=employee,
        user_id=user_id,
        name="Future Allowance",
        code="BW-FUTURE",
        amount="700.00",
        classification=AllowanceType.EARNING_REGULAR,
        start_date=date(2026, 1, 1),
    )

    period = create_period(
        database,
        user_id=user_id,
        year=2025,
        month=12,
    )

    database.session.commit()

    period_id = period.id
    employee_id = employee.id

    PayrollService.process_period(
        period=period,
        processed_by_user_id=user_id,
        currency="BWP",
    )

    database.session.remove()

    record = PayrollRecord.query.filter_by(
        payroll_period_id=period_id,
        employee_id=employee_id,
    ).one()

    assert record.allowances_total == ZERO
    assert record.gross_pay == Decimal("18000.00")
    assert record.paye == Decimal("2337.50")
    assert record.net_pay == Decimal("15662.50")
    assert record.allowances == []


def test_prior_year_fallback_is_exposed_and_audited(
    database,
    botswana_setup,
):
    """Expose the provisional prior-year rule fallback everywhere."""

    rule_set = database.session.get(
        StatutoryRuleSet,
        botswana_setup["rule_set_id"],
    )
    rule_set.effective_to = date(2025, 12, 31)

    period = create_period(
        database,
        user_id=botswana_setup["user_id"],
        year=2026,
        month=1,
    )

    database.session.commit()

    period_id = period.id

    result = PayrollService.process_period(
        period=period,
        processed_by_user_id=botswana_setup["user_id"],
        currency="BWP",
    )

    assert result.created_count == 1
    assert result.provisional_rule_used is True
    assert result.rule_effective_to == date(2025, 12, 31)
    assert result.calculation_date == date(2026, 1, 31)

    database.session.remove()

    period = database.session.get(
        PayrollPeriod,
        period_id,
    )

    assert period.status == "Processed"

    audit = AuditLog.query.filter_by(
        action="Payroll Processed",
        entity_type="PayrollPeriod",
        entity_id=period_id,
    ).one()

    assert "PROVISIONAL FALLBACK" in audit.description
    assert "prior-year statutory rates were used" in audit.description
