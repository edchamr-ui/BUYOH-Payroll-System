from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import pytest
from app.services.payroll_service import PayrollConfigurationError, PayrollService
from app.services.payslip_service import PayslipService


class FakeQuery:
    def __init__(self,v): self.v=v
    def filter_by(self,**kwargs): return self
    def one_or_none(self): return self.v


def employee(): return SimpleNamespace(id=7, employee_number="UK-007", basic_salary=Decimal("3000"))
def period(): return SimpleNamespace(id=11)
def entry(**o):
    v=dict(entitlement_reference="CHILD-2026-001",shared_pay_period_start=date(2026,8,3),average_weekly_earnings=Decimal("500"),allocated_days=70,paid_days=7,salary_withheld=Decimal("700"),eligibility_confirmed=True,curtailment_notice_received=True,partner_declaration_received=True);v.update(o);return SimpleNamespace(**v)
def result(**o):
    v=dict(amount=Decimal("194.32"),average_weekly_earnings=Decimal("500"),weekly_rate=Decimal("194.32"),allocated_days=70,payable_days=7,prior_paid_days=0,remaining_allocated_days=63);v.update(o);return SimpleNamespace(**v)
def configure(monkeypatch,e):
    import app.services.payroll_service as m
    monkeypatch.setattr(m,"PayrollShPPInput",SimpleNamespace(query=FakeQuery(e)))
    monkeypatch.setattr(PayrollService,"_uk_prior_shpp_paid_days",classmethod(lambda cls,*args:0))
def calculate(monkeypatch,e=None,**o):
    configure(monkeypatch,e)
    engine=SimpleNamespace(calculate_statutory_shared_parental_pay=lambda **kwargs:result(**o))
    return PayrollService._uk_shpp_snapshot(employee=employee(),period=period(),statutory_engine=engine,statutory_config=SimpleNamespace(),calculation_date=date(2026,8,31))


def test_no_input_returns_zero(monkeypatch): assert calculate(monkeypatch)==(Decimal("0.00"),Decimal("0.00"),{})
def test_shpp_replaces_salary(monkeypatch):
    amount,withheld,snapshot=calculate(monkeypatch,entry());assert amount==Decimal("194.32");assert withheld==Decimal("700");assert snapshot["uk_shpp_remaining_allocated_days"]==63
def test_snapshot_preserves_entitlement(monkeypatch):
    _,_,s=calculate(monkeypatch,entry());assert s["uk_shpp_entitlement_reference"]=="CHILD-2026-001";assert s["uk_shpp_allocated_days"]==70
@pytest.mark.parametrize("field,message",(("eligibility_confirmed","eligibility"),("curtailment_notice_received","curtailment"),("partner_declaration_received","partner declaration")))
def test_required_evidence(monkeypatch,field,message):
    configure(monkeypatch,entry(**{field:False}))
    with pytest.raises(PayrollConfigurationError,match=message): PayrollService._uk_shpp_snapshot(employee=employee(),period=period(),statutory_engine=SimpleNamespace(),statutory_config=SimpleNamespace(),calculation_date=date(2026,8,31))
def test_withholding_limit(monkeypatch):
    configure(monkeypatch,entry(salary_withheld=Decimal("3000.01")))
    with pytest.raises(PayrollConfigurationError,match="cannot exceed"): PayrollService._uk_shpp_snapshot(employee=employee(),period=period(),statutory_engine=SimpleNamespace(),statutory_config=SimpleNamespace(),calculation_date=date(2026,8,31))
def test_prior_days_forwarded(monkeypatch):
    configure(monkeypatch,entry());monkeypatch.setattr(PayrollService,"_uk_prior_shpp_paid_days",classmethod(lambda cls,*args:14));captured={}
    def cap(**kwargs): captured.update(kwargs);return result(prior_paid_days=14,remaining_allocated_days=49)
    PayrollService._uk_shpp_snapshot(employee=employee(),period=period(),statutory_engine=SimpleNamespace(calculate_statutory_shared_parental_pay=cap),statutory_config=SimpleNamespace(),calculation_date=date(2026,8,31));assert captured["prior_paid_days"]==14
def test_history_sum(monkeypatch):
    monkeypatch.setattr(PayrollService,"_uk_shpp_history_records",staticmethod(lambda *args:[SimpleNamespace(uk_shpp_paid_days=7),SimpleNamespace(uk_shpp_paid_days=None),SimpleNamespace(uk_shpp_paid_days=5)]));assert PayrollService._uk_prior_shpp_paid_days(7,"REF",date(2026,8,31))==12
def test_payslip_format(): assert PayslipService._money(Decimal("1194.32"))=="1,194.32"
