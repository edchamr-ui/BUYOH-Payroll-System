"""add UK SMP operational fields

Revision ID: e8f1a6c39d42
Revises: d7e9c42b881a
"""

from alembic import op
import sqlalchemy as sa


revision = "e8f1a6c39d42"
down_revision = "d7e9c42b881a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payroll_smp_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("maternity_pay_period_start", sa.Date(), nullable=False),
        sa.Column("average_weekly_earnings", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_days", sa.Integer(), nullable=False),
        sa.Column("salary_withheld", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("eligibility_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("matb1_received", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("average_weekly_earnings >= 0", name="ck_payroll_smp_input_awe_non_negative"),
        sa.CheckConstraint("paid_days >= 0", name="ck_payroll_smp_input_paid_days_non_negative"),
        sa.CheckConstraint("salary_withheld >= 0", name="ck_payroll_smp_input_salary_withheld_non_negative"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payroll_period_id", "employee_id", name="uq_payroll_smp_input_period_employee"),
    )
    op.create_index("ix_payroll_smp_inputs_employee_id", "payroll_smp_inputs", ["employee_id"])
    op.create_index("ix_payroll_smp_inputs_payroll_period_id", "payroll_smp_inputs", ["payroll_period_id"])

    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.add_column(sa.Column("uk_smp_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("uk_smp_salary_withheld", sa.Numeric(12, 2), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("uk_smp_average_weekly_earnings", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("uk_smp_higher_weekly_rate", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("uk_smp_standard_weekly_rate", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("uk_smp_paid_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_smp_prior_paid_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_smp_higher_rate_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_smp_standard_rate_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_smp_mpp_start_date", sa.Date()))
        batch_op.add_column(sa.Column("uk_smp_eligibility_confirmed", sa.Boolean()))
        batch_op.add_column(sa.Column("uk_smp_matb1_received", sa.Boolean()))
        batch_op.create_check_constraint(
            "ck_payroll_record_uk_smp_amounts_non_negative",
            "uk_smp_amount >= 0 AND uk_smp_salary_withheld >= 0",
        )


def downgrade():
    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.drop_constraint("ck_payroll_record_uk_smp_amounts_non_negative", type_="check")
        for column in (
            "uk_smp_matb1_received",
            "uk_smp_eligibility_confirmed",
            "uk_smp_mpp_start_date",
            "uk_smp_standard_rate_days",
            "uk_smp_higher_rate_days",
            "uk_smp_prior_paid_days",
            "uk_smp_paid_days",
            "uk_smp_standard_weekly_rate",
            "uk_smp_higher_weekly_rate",
            "uk_smp_average_weekly_earnings",
            "uk_smp_salary_withheld",
            "uk_smp_amount",
        ):
            batch_op.drop_column(column)

    op.drop_index("ix_payroll_smp_inputs_payroll_period_id", table_name="payroll_smp_inputs")
    op.drop_index("ix_payroll_smp_inputs_employee_id", table_name="payroll_smp_inputs")
    op.drop_table("payroll_smp_inputs")
