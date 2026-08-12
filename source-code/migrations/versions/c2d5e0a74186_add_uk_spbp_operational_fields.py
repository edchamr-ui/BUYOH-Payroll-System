"""add UK SPBP operational fields

Revision ID: c2d5e0a74186
Revises: b1c4d9f63075
"""

from alembic import op
import sqlalchemy as sa


revision = "c2d5e0a74186"
down_revision = "b1c4d9f63075"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payroll_spbp_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("entitlement_reference", sa.String(80), nullable=False),
        sa.Column("bereavement_date", sa.Date(), nullable=False),
        sa.Column("bereavement_pay_period_start", sa.Date(), nullable=False),
        sa.Column("average_weekly_earnings", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_days", sa.Integer(), nullable=False),
        sa.Column(
            "salary_withheld",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "eligibility_confirmed",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "notice_received",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "declaration_received",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("notes", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "average_weekly_earnings >= 0",
            name="ck_payroll_spbp_input_awe_non_negative",
        ),
        sa.CheckConstraint(
            "paid_days >= 0",
            name="ck_payroll_spbp_input_paid_days_non_negative",
        ),
        sa.CheckConstraint(
            "salary_withheld >= 0",
            name="ck_payroll_spbp_input_salary_withheld_non_negative",
        ),
        sa.CheckConstraint(
            "bereavement_pay_period_start >= bereavement_date",
            name="ck_payroll_spbp_input_period_after_bereavement",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["payroll_period_id"],
            ["payroll_periods.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payroll_period_id",
            "employee_id",
            name="uq_payroll_spbp_input_period_employee",
        ),
    )
    op.create_index(
        "ix_payroll_spbp_inputs_employee_id",
        "payroll_spbp_inputs",
        ["employee_id"],
    )
    op.create_index(
        "ix_payroll_spbp_inputs_payroll_period_id",
        "payroll_spbp_inputs",
        ["payroll_period_id"],
    )
    op.create_index(
        "ix_payroll_spbp_inputs_entitlement_reference",
        "payroll_spbp_inputs",
        ["entitlement_reference"],
    )

    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.add_column(
            sa.Column(
                "uk_spbp_amount",
                sa.Numeric(12, 2),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "uk_spbp_salary_withheld",
                sa.Numeric(12, 2),
                server_default="0",
                nullable=False,
            )
        )
        for name, kind in (
            ("uk_spbp_average_weekly_earnings", sa.Numeric(12, 2)),
            ("uk_spbp_weekly_rate", sa.Numeric(12, 2)),
            ("uk_spbp_paid_days", sa.Integer()),
            ("uk_spbp_prior_paid_days", sa.Integer()),
            ("uk_spbp_remaining_paid_days", sa.Integer()),
            ("uk_spbp_entitlement_reference", sa.String(80)),
            ("uk_spbp_bereavement_date", sa.Date()),
            ("uk_spbp_period_start_date", sa.Date()),
            ("uk_spbp_eligibility_confirmed", sa.Boolean()),
            ("uk_spbp_notice_received", sa.Boolean()),
            ("uk_spbp_declaration_received", sa.Boolean()),
        ):
            batch_op.add_column(sa.Column(name, kind))
        batch_op.create_check_constraint(
            "ck_payroll_record_uk_spbp_amounts_non_negative",
            "uk_spbp_amount >= 0 AND uk_spbp_salary_withheld >= 0",
        )


def downgrade():
    with op.batch_alter_table("payroll_records") as batch_op:
        batch_op.drop_constraint(
            "ck_payroll_record_uk_spbp_amounts_non_negative",
            type_="check",
        )
        for name in (
            "uk_spbp_declaration_received",
            "uk_spbp_notice_received",
            "uk_spbp_eligibility_confirmed",
            "uk_spbp_period_start_date",
            "uk_spbp_bereavement_date",
            "uk_spbp_entitlement_reference",
            "uk_spbp_remaining_paid_days",
            "uk_spbp_prior_paid_days",
            "uk_spbp_paid_days",
            "uk_spbp_weekly_rate",
            "uk_spbp_average_weekly_earnings",
            "uk_spbp_salary_withheld",
            "uk_spbp_amount",
        ):
            batch_op.drop_column(name)

    op.drop_index(
        "ix_payroll_spbp_inputs_entitlement_reference",
        table_name="payroll_spbp_inputs",
    )
    op.drop_index(
        "ix_payroll_spbp_inputs_payroll_period_id",
        table_name="payroll_spbp_inputs",
    )
    op.drop_index(
        "ix_payroll_spbp_inputs_employee_id",
        table_name="payroll_spbp_inputs",
    )
    op.drop_table("payroll_spbp_inputs")
