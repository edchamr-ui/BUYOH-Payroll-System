"""add UK ShPP operational fields

Revision ID: b1c4d9f63075
Revises: a0b3c8e52f64
"""
from alembic import op
import sqlalchemy as sa
revision = "b1c4d9f63075"
down_revision = "a0b3c8e52f64"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("payroll_shpp_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("entitlement_reference", sa.String(80), nullable=False),
        sa.Column("shared_pay_period_start", sa.Date(), nullable=False),
        sa.Column("average_weekly_earnings", sa.Numeric(12,2), nullable=False),
        sa.Column("allocated_days", sa.Integer(), nullable=False),
        sa.Column("paid_days", sa.Integer(), nullable=False),
        sa.Column("salary_withheld", sa.Numeric(12,2), server_default="0", nullable=False),
        sa.Column("eligibility_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("curtailment_notice_received", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("partner_declaration_received", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.String(500)), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("average_weekly_earnings >= 0", name="ck_payroll_shpp_input_awe_non_negative"),
        sa.CheckConstraint("allocated_days >= 0 AND allocated_days <= 259", name="ck_payroll_shpp_input_allocated_days"),
        sa.CheckConstraint("paid_days >= 0", name="ck_payroll_shpp_input_paid_days_non_negative"),
        sa.CheckConstraint("salary_withheld >= 0", name="ck_payroll_shpp_input_salary_withheld_non_negative"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payroll_period_id", "employee_id", name="uq_payroll_shpp_input_period_employee"))
    op.create_index("ix_payroll_shpp_inputs_employee_id", "payroll_shpp_inputs", ["employee_id"])
    op.create_index("ix_payroll_shpp_inputs_payroll_period_id", "payroll_shpp_inputs", ["payroll_period_id"])
    op.create_index("ix_payroll_shpp_inputs_entitlement_reference", "payroll_shpp_inputs", ["entitlement_reference"])
    with op.batch_alter_table("payroll_records") as b:
        for name, kind in (("uk_shpp_amount",sa.Numeric(12,2)),("uk_shpp_salary_withheld",sa.Numeric(12,2))):
            b.add_column(sa.Column(name, kind, server_default="0", nullable=False))
        for name, kind in (
            ("uk_shpp_average_weekly_earnings",sa.Numeric(12,2)),("uk_shpp_weekly_rate",sa.Numeric(12,2)),
            ("uk_shpp_allocated_days",sa.Integer()),("uk_shpp_paid_days",sa.Integer()),
            ("uk_shpp_prior_paid_days",sa.Integer()),("uk_shpp_remaining_allocated_days",sa.Integer()),
            ("uk_shpp_entitlement_reference",sa.String(80)),("uk_shpp_period_start_date",sa.Date()),
            ("uk_shpp_eligibility_confirmed",sa.Boolean()),("uk_shpp_curtailment_notice_received",sa.Boolean()),
            ("uk_shpp_partner_declaration_received",sa.Boolean())):
            b.add_column(sa.Column(name, kind))
        b.create_check_constraint("ck_payroll_record_uk_shpp_amounts_non_negative", "uk_shpp_amount >= 0 AND uk_shpp_salary_withheld >= 0")


def downgrade():
    with op.batch_alter_table("payroll_records") as b:
        b.drop_constraint("ck_payroll_record_uk_shpp_amounts_non_negative", type_="check")
        for name in ("uk_shpp_partner_declaration_received","uk_shpp_curtailment_notice_received","uk_shpp_eligibility_confirmed","uk_shpp_period_start_date","uk_shpp_entitlement_reference","uk_shpp_remaining_allocated_days","uk_shpp_prior_paid_days","uk_shpp_paid_days","uk_shpp_allocated_days","uk_shpp_weekly_rate","uk_shpp_average_weekly_earnings","uk_shpp_salary_withheld","uk_shpp_amount"):
            b.drop_column(name)
    op.drop_index("ix_payroll_shpp_inputs_entitlement_reference", table_name="payroll_shpp_inputs")
    op.drop_index("ix_payroll_shpp_inputs_payroll_period_id", table_name="payroll_shpp_inputs")
    op.drop_index("ix_payroll_shpp_inputs_employee_id", table_name="payroll_shpp_inputs")
    op.drop_table("payroll_shpp_inputs")
