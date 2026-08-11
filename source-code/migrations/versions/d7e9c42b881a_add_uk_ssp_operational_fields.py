"""add UK SSP operational fields

Revision ID: d7e9c42b881a
Revises: a41d5e6f7b82
"""

from alembic import op
import sqlalchemy as sa


revision = "d7e9c42b881a"
down_revision = "a41d5e6f7b82"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payroll_ssp_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("sickness_start_date", sa.Date(), nullable=False),
        sa.Column("average_weekly_earnings", sa.Numeric(12, 2), nullable=False),
        sa.Column("qualifying_days_per_week", sa.Integer(), nullable=False),
        sa.Column("qualifying_days_sick", sa.Integer(), nullable=False),
        sa.Column("salary_withheld", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("average_weekly_earnings >= 0", name="ck_payroll_ssp_input_awe_non_negative"),
        sa.CheckConstraint("qualifying_days_per_week BETWEEN 1 AND 7", name="ck_payroll_ssp_input_days_per_week"),
        sa.CheckConstraint("qualifying_days_sick >= 0", name="ck_payroll_ssp_input_sick_days_non_negative"),
        sa.CheckConstraint("salary_withheld >= 0", name="ck_payroll_ssp_input_salary_withheld_non_negative"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payroll_period_id", "employee_id", name="uq_payroll_ssp_input_period_employee"),
    )
    op.create_index("ix_payroll_ssp_inputs_employee_id", "payroll_ssp_inputs", ["employee_id"])
    op.create_index("ix_payroll_ssp_inputs_payroll_period_id", "payroll_ssp_inputs", ["payroll_period_id"])

    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.add_column(sa.Column("uk_ssp_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("uk_ssp_salary_withheld", sa.Numeric(12, 2), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("uk_ssp_average_weekly_earnings", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("uk_ssp_weekly_rate", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("uk_ssp_qualifying_days_per_week", sa.Integer()))
        batch_op.add_column(sa.Column("uk_ssp_qualifying_days_sick", sa.Integer()))
        batch_op.add_column(sa.Column("uk_ssp_payable_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_ssp_prior_paid_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_ssp_sickness_start_date", sa.Date()))
        batch_op.create_check_constraint(
            "ck_payroll_record_uk_ssp_amounts_non_negative",
            "uk_ssp_amount >= 0 AND uk_ssp_salary_withheld >= 0",
        )


def downgrade():
    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.drop_constraint("ck_payroll_record_uk_ssp_amounts_non_negative", type_="check")
        for column in (
            "uk_ssp_sickness_start_date",
            "uk_ssp_prior_paid_days",
            "uk_ssp_payable_days",
            "uk_ssp_qualifying_days_sick",
            "uk_ssp_qualifying_days_per_week",
            "uk_ssp_weekly_rate",
            "uk_ssp_average_weekly_earnings",
            "uk_ssp_salary_withheld",
            "uk_ssp_amount",
        ):
            batch_op.drop_column(column)

    op.drop_index("ix_payroll_ssp_inputs_payroll_period_id", table_name="payroll_ssp_inputs")
    op.drop_index("ix_payroll_ssp_inputs_employee_id", table_name="payroll_ssp_inputs")
    op.drop_table("payroll_ssp_inputs")
