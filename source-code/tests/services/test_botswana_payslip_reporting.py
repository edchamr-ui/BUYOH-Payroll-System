"""Payslip and reporting integration tests for Botswana payroll."""

from decimal import Decimal

from reportlab.platypus import Paragraph, Table

import app.services.payslip_service as payslip_module
from app.models.employee import Employee
from app.models.payroll_record import PayrollRecord
from app.reports.paye_service import PayeReportingService
from app.reports.services import ReportingService
from app.services.payroll_service import PayrollService
from app.services.payslip_service import PayslipService
from tests.services.test_botswana_payroll_integration import (
    botswana_setup,
    create_period,
)
from tests.services.test_botswana_production_flow import (
    add_allowance,
    add_deduction,
    add_employee,
)


ZERO = Decimal("0.00")


def build_botswana_payroll(database, botswana_setup):
    """Create and process the three-employee Botswana test payroll."""

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
        code="BW-COMMISSION-REPORT",
        amount="700.00",
        classification="Commission",
    )

    add_deduction(
        database,
        employee=resident,
        user_id=user_id,
        name="Approved Pension",
        code="BW-PENSION-REPORT",
        amount="200.00",
        tax_deductible=True,
    )

    add_allowance(
        database,
        employee=bonus_employee,
        user_id=user_id,
        name="Annual Performance Bonus",
        code="BW-BONUS-REPORT",
        amount="4000.00",
        classification="Bonus",
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

    PayrollService.process_period(
        period=period,
        processed_by_user_id=user_id,
        currency="BWP",
    )

    database.session.remove()

    records = {
        record.employee_id: record
        for record in PayrollRecord.query.filter_by(
            payroll_period_id=period_id,
        ).all()
    }

    return {
        "period_id": period_id,
        "department_id": department_id,
        "resident": records[resident_id],
        "non_resident": records[non_resident_id],
        "bonus": records[bonus_employee_id],
    }


def extract_story_text(item):
    """Recursively extract visible text from ReportLab flowables."""

    if isinstance(item, Paragraph):
        return [item.getPlainText()]

    if isinstance(item, Table):
        text = []

        for row in item._cellvalues:
            for cell in row:
                text.extend(extract_story_text(cell))

        return text

    if isinstance(item, (list, tuple)):
        text = []

        for child in item:
            text.extend(extract_story_text(child))

        return text

    if isinstance(item, str):
        return [item]

    return []


def capture_payslip_story(monkeypatch):
    """Replace the ReportLab document with an in-memory capture."""

    captured = {}

    class CapturingDocument:
        def __init__(self, *_args, **_kwargs):
            pass

        def build(self, story, **_kwargs):
            captured["story"] = story

    monkeypatch.setattr(
        payslip_module,
        "SimpleDocTemplate",
        CapturingDocument,
    )

    monkeypatch.setattr(
        payslip_module.CompanySettingsService,
        "get_company_profile",
        staticmethod(
            lambda: {
                "company_name": "Botswana Integration Company",
                "physical_address": "Gaborone, Botswana",
                "currency": "BWP",
                "payslip_footer": "",
            }
        ),
    )

    monkeypatch.setattr(
        payslip_module.CompanySettingsService,
        "get_logo_file_path",
        staticmethod(lambda: None),
    )

    return captured


def test_botswana_reports_reconcile_to_persisted_records(
    database,
    botswana_setup,
):
    """Reconcile payroll, PAYE, and department reporting totals."""

    payroll = build_botswana_payroll(
        database,
        botswana_setup,
    )

    period_id = payroll["period_id"]

    payroll_report = ReportingService.get_payroll_summary(
        period_id=period_id,
    )
    payroll_totals = payroll_report["totals"]

    assert payroll_totals["employee_count"] == 3
    assert payroll_totals["basic_salary"] == Decimal("29000.00")
    assert payroll_totals["allowances_total"] == Decimal("4700.00")
    assert payroll_totals["gross_pay"] == Decimal("33700.00")
    assert payroll_totals["employee_nssa"] == ZERO
    assert payroll_totals["employer_nssa"] == ZERO
    assert payroll_totals["paye"] == Decimal("3012.50")
    assert payroll_totals["aids_levy"] == ZERO
    assert payroll_totals["total_tax"] == Decimal("3012.50")
    assert payroll_totals["other_deductions"] == Decimal("200.00")
    assert payroll_totals["total_deductions"] == Decimal("3212.50")
    assert payroll_totals["net_pay"] == Decimal("30487.50")
    assert payroll_totals["employer_cost"] == Decimal("33700.00")
    assert payroll_totals["total_nssa"] == ZERO

    persisted_regular_paye = sum(
        (
            record.regular_paye
            for record in payroll_report["records"]
        ),
        ZERO,
    )
    persisted_irregular_paye = sum(
        (
            record.irregular_paye
            for record in payroll_report["records"]
        ),
        ZERO,
    )

    assert persisted_regular_paye == Decimal("2812.50")
    assert persisted_irregular_paye == Decimal("200.00")
    assert (
        persisted_regular_paye
        + persisted_irregular_paye
        == payroll_totals["paye"]
    )

    paye_report = PayeReportingService.get_report(
        period_id=period_id,
    )
    paye_totals = paye_report["totals"]

    assert len(paye_report["rows"]) == 3
    assert paye_totals["employee_count"] == 3
    assert paye_totals["gross_pay"] == Decimal("33700.00")
    assert paye_totals["employee_nssa"] == ZERO
    assert paye_totals["taxable_income"] == Decimal("33700.00")
    assert paye_totals["paye"] == Decimal("3012.50")
    assert paye_totals["aids_levy"] == ZERO
    assert paye_totals["total_tax"] == Decimal("3012.50")
    assert paye_totals["average_paye"] == Decimal(
        "1004.166666666666666666666667"
    )

    department_report = ReportingService.get_department_summary(
        period_id=period_id,
    )
    department_totals = department_report["totals"]

    assert department_totals["department_count"] == 1
    assert department_totals["employee_count"] == 3
    assert department_totals["gross_pay"] == Decimal("33700.00")
    assert department_totals["paye"] == Decimal("3012.50")
    assert department_totals["employee_nssa"] == ZERO
    assert department_totals["employer_nssa"] == ZERO
    assert department_totals["aids_levy"] == ZERO
    assert department_totals["total_deductions"] == Decimal("3212.50")
    assert department_totals["net_pay"] == Decimal("30487.50")
    assert department_totals["employer_cost"] == Decimal("33700.00")

    department = department_report["departments"][0]

    assert department["department_id"] == payroll["department_id"]
    assert department["employee_count"] == 3
    assert department["gross_pay"] == Decimal("33700.00")
    assert department["net_pay"] == Decimal("30487.50")


def test_bonus_payslip_displays_bwp_and_split_paye(
    database,
    botswana_setup,
    monkeypatch,
    tmp_path,
):
    """Display Botswana currency and regular/irregular PAYE separately."""

    payroll = build_botswana_payroll(
        database,
        botswana_setup,
    )
    bonus_record = payroll["bonus"]

    captured = capture_payslip_story(monkeypatch)

    PayslipService._create_pdf(
        payroll_record=bonus_record,
        output_path=tmp_path / "bonus-payslip.pdf",
    )

    visible_text = " | ".join(
        extract_story_text(captured["story"])
    )

    assert "Botswana Integration Company" in visible_text
    assert "BWP 7,800.00" in visible_text
    assert "(All figures in BWP)" in visible_text
    assert "PAYE — Regular" in visible_text
    assert "PAYE — Irregular" in visible_text
    assert "200.00" in visible_text
    assert "NSSA Deduction" in visible_text
    assert "AIDS Levy" in visible_text


def test_regular_payslip_uses_combined_paye_label(
    database,
    botswana_setup,
    monkeypatch,
    tmp_path,
):
    """Use the simple PAYE row when no irregular PAYE exists."""

    payroll = build_botswana_payroll(
        database,
        botswana_setup,
    )
    resident_record = payroll["resident"]

    captured = capture_payslip_story(monkeypatch)

    PayslipService._create_pdf(
        payroll_record=resident_record,
        output_path=tmp_path / "resident-payslip.pdf",
    )

    visible_text = " | ".join(
        extract_story_text(captured["story"])
    )

    assert "BWP 16,037.50" in visible_text
    assert "(All figures in BWP)" in visible_text
    assert "PAYE" in visible_text
    assert "2,462.50" in visible_text
    assert "PAYE — Regular" not in visible_text
    assert "PAYE — Irregular" not in visible_text
    assert "Approved Pension" in visible_text
    assert "200.00" in visible_text
