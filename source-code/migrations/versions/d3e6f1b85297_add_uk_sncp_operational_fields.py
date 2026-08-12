"""add UK SNCP operational fields

Revision ID: d3e6f1b85297
Revises: c2d5e0a74186
"""

from alembic import op
import sqlalchemy as sa


revision = "d3e6f1b85297"
down_revision = "c2d5e0a74186"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payroll_sncp_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("entitlement_reference", sa.String(80), nullable=False),
        sa.Column("baby_date_of_birth", sa.Date(), nullable=False),
        sa.Column("neonatal_care_start_date", sa.Date(), nullable=False),
        sa.Column("neonatal_care_through_date", sa.Date(), nullable=False),
        sa.Column("neonatal_pay_period_start", sa.Date(), nullable=False),
        sa.Column("average_weekly_earnings", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_days", sa.Integer(), nullable=False),
        sa.Column("salary_withheld", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("eligibility_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("service_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("neonatal_care_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notice_received", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("declaration_received", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("average_weekly_earnings >= 0", name="ck_payroll_sncp_input_awe_non_negative"),
        sa.CheckConstraint("paid_days >= 0", name="ck_payroll_sncp_input_paid_days_non_negative"),
        sa.CheckConstraint("salary_withheld >= 0", name="ck_payroll_sncp_input_salary_withheld_non_negative"),
        sa.CheckConstraint("neonatal_care_start_date >= baby_date_of_birth", name="ck_payroll_sncp_input_care_after_birth"),
        sa.CheckConstraint("neonatal_care_through_date >= neonatal_care_start_date", name="ck_payroll_sncp_input_care_date_order"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payroll_period_id", "employee_id", name="uq_payroll_sncp_input_period_employee"),
    )
    op.create_index("ix_payroll_sncp_inputs_employee_id", "payroll_sncp_inputs", ["employee_id"])
    op.create_index("ix_payroll_sncp_inputs_payroll_period_id", "payroll_sncp_inputs", ["payroll_period_id"])
    op.create_index("ix_payroll_sncp_inputs_entitlement_reference", "payroll_sncp_inputs", ["entitlement_reference"])

    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.add_column(sa.Column("uk_sncp_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("uk_sncp_salary_withheld", sa.Numeric(12, 2), server_default="0", nullable=False))
        for name, kind in (
            ("uk_sncp_average_weekly_earnings", sa.Numeric(12, 2)),
            ("uk_sncp_weekly_rate", sa.Numeric(12, 2)),
            ("uk_sncp_accrued_weeks", sa.Integer()),
            ("uk_sncp_accrued_days", sa.Integer()),
            ("uk_sncp_paid_days", sa.Integer()),
            ("uk_sncp_prior_paid_days", sa.Integer()),
            ("uk_sncp_remaining_accrued_days", sa.Integer()),
            ("uk_sncp_entitlement_reference", sa.String(80)),
            ("uk_sncp_baby_date_of_birth", sa.Date()),
            ("uk_sncp_care_start_date", sa.Date()),
            ("uk_sncp_care_through_date", sa.Date()),
            ("uk_sncp_period_start_date", sa.Date()),
            ("uk_sncp_eligibility_confirmed", sa.Boolean()),
            ("uk_sncp_service_confirmed", sa.Boolean()),
            ("uk_sncp_neonatal_care_confirmed", sa.Boolean()),
            ("uk_sncp_notice_received", sa.Boolean()),
            ("uk_sncp_declaration_received", sa.Boolean()),
        ):
            batch_op.add_column(sa.Column(name, kind))
        batch_op.create_check_constraint(
            "ck_payroll_record_uk_sncp_amounts_non_negative",
            "uk_sncp_amount >= 0 AND uk_sncp_salary_withheld >= 0",
        )


def downgrade():
    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.drop_constraint("ck_payroll_record_uk_sncp_amounts_non_negative", type_="check")
        for name in (
            "uk_sncp_declaration_received", "uk_sncp_notice_received",
            "uk_sncp_neonatal_care_confirmed", "uk_sncp_service_confirmed",
            "uk_sncp_eligibility_confirmed", "uk_sncp_period_start_date",
            "uk_sncp_care_through_date", "uk_sncp_care_start_date",
            "uk_sncp_baby_date_of_birth", "uk_sncp_entitlement_reference",
            "uk_sncp_remaining_accrued_days", "uk_sncp_prior_paid_days",
            "uk_sncp_paid_days", "uk_sncp_accrued_days",
            "uk_sncp_accrued_weeks", "uk_sncp_weekly_rate",
            "uk_sncp_average_weekly_earnings", "uk_sncp_salary_withheld",
            "uk_sncp_amount",
        ):
            batch_op.drop_column(name)
    op.drop_index("ix_payroll_sncp_inputs_entitlement_reference", table_name="payroll_sncp_inputs")
    op.drop_index("ix_payroll_sncp_inputs_payroll_period_id", table_name="payroll_sncp_inputs")
    op.drop_index("ix_payroll_sncp_inputs_employee_id", table_name="payroll_sncp_inputs")
    op.drop_table("payroll_sncp_inputs")
