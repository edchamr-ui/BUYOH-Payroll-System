"""add UK SAP operational fields

Revision ID: a0b3c8e52f64
Revises: f9a2b7d41e53
"""

from alembic import op
import sqlalchemy as sa


revision = "a0b3c8e52f64"
down_revision = "f9a2b7d41e53"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payroll_sap_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("adoption_pay_period_start", sa.Date(), nullable=False),
        sa.Column("average_weekly_earnings", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_days", sa.Integer(), nullable=False),
        sa.Column("salary_withheld", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("eligibility_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("adoption_evidence_received", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("average_weekly_earnings >= 0", name="ck_payroll_sap_input_awe_non_negative"),
        sa.CheckConstraint("paid_days >= 0", name="ck_payroll_sap_input_paid_days_non_negative"),
        sa.CheckConstraint("salary_withheld >= 0", name="ck_payroll_sap_input_salary_withheld_non_negative"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payroll_period_id", "employee_id", name="uq_payroll_sap_input_period_employee"),
    )
    op.create_index("ix_payroll_sap_inputs_employee_id", "payroll_sap_inputs", ["employee_id"])
    op.create_index("ix_payroll_sap_inputs_payroll_period_id", "payroll_sap_inputs", ["payroll_period_id"])

    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.add_column(sa.Column("uk_sap_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("uk_sap_salary_withheld", sa.Numeric(12, 2), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("uk_sap_average_weekly_earnings", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("uk_sap_higher_weekly_rate", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("uk_sap_standard_weekly_rate", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("uk_sap_paid_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_sap_prior_paid_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_sap_higher_rate_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_sap_standard_rate_days", sa.Integer()))
        batch_op.add_column(sa.Column("uk_sap_app_start_date", sa.Date()))
        batch_op.add_column(sa.Column("uk_sap_eligibility_confirmed", sa.Boolean()))
        batch_op.add_column(sa.Column("uk_sap_adoption_evidence_received", sa.Boolean()))
        batch_op.create_check_constraint(
            "ck_payroll_record_uk_sap_amounts_non_negative",
            "uk_sap_amount >= 0 AND uk_sap_salary_withheld >= 0",
        )


def downgrade():
    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.drop_constraint("ck_payroll_record_uk_sap_amounts_non_negative", type_="check")
        for column in (
            "uk_sap_adoption_evidence_received",
            "uk_sap_eligibility_confirmed",
            "uk_sap_app_start_date",
            "uk_sap_standard_rate_days",
            "uk_sap_higher_rate_days",
            "uk_sap_prior_paid_days",
            "uk_sap_paid_days",
            "uk_sap_standard_weekly_rate",
            "uk_sap_higher_weekly_rate",
            "uk_sap_average_weekly_earnings",
            "uk_sap_salary_withheld",
            "uk_sap_amount",
        ):
            batch_op.drop_column(column)

    op.drop_index("ix_payroll_sap_inputs_payroll_period_id", table_name="payroll_sap_inputs")
    op.drop_index("ix_payroll_sap_inputs_employee_id", table_name="payroll_sap_inputs")
    op.drop_table("payroll_sap_inputs")
