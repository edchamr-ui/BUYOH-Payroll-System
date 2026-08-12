from datetime import date
from types import SimpleNamespace
from flask import Flask
from app.payroll_periods.forms import PayrollShPPInputForm
from app.payroll_periods.routes import can_manage_shpp,validate_shpp_input


def build_form(**overrides):
    data=dict(entitlement_reference="CHILD-2026-001",shared_pay_period_start="2026-08-03",average_weekly_earnings="500",allocated_days="70",paid_days="7",salary_withheld="700",eligibility_confirmed="y",curtailment_notice_received="y",partner_declaration_received="y",notes="Checked")
    data.update(overrides);data={k:v for k,v in data.items() if v is not None};app=Flask(__name__);app.config.update(SECRET_KEY="test",WTF_CSRF_ENABLED=False)
    with app.test_request_context(method="POST",data=data): form=PayrollShPPInputForm();form.validate();return form
def period(status="Draft",open=True): return SimpleNamespace(status=status,end_date=date(2026,8,31),payroll_year=SimpleNamespace(is_open=open))
def test_valid(): assert not build_form().errors
def test_reference_required(): assert build_form(entitlement_reference="").entitlement_reference.errors
def test_allocation_maximum(): assert build_form(allocated_days="260").allocated_days.errors==["Enter between 0 and 259 allocated days."]
def test_paid_days_limit(): assert build_form(paid_days="32").paid_days.errors==["Enter between 0 and 31 paid days."]
def test_all_evidence_required():
    assert build_form(eligibility_confirmed=None).eligibility_confirmed.errors
    assert build_form(curtailment_notice_received=None).curtailment_notice_received.errors
    assert build_form(partner_declaration_received=None).partner_declaration_received.errors
def test_draft_locking(): assert can_manage_shpp(period()) and not can_manage_shpp(period("Processed")) and not can_manage_shpp(period(open=False))
def test_start_date_validation(): assert validate_shpp_input(build_form(shared_pay_period_start="2026-09-01"),period())==["Shared pay period start cannot be after the payroll period end date."]
def test_paid_days_cannot_exceed_allocation(): assert validate_shpp_input(build_form(allocated_days="5",paid_days="7"),period())==["Paid days cannot exceed the transferred allocation."]
def test_prior_start_allowed(): assert validate_shpp_input(build_form(),period())==[]
def test_notes_limit(): assert build_form(notes="x"*501).notes.errors
