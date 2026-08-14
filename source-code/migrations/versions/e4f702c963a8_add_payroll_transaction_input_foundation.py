"""add payroll transaction input foundation

Revision ID: e4f702c963a8
Revises: d3e6f1b85297
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa


revision = "e4f702c963a8"
down_revision = "d3e6f1b85297"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payroll_overtime_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=True),
        sa.Column("hours", sa.Numeric(10, 2), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(12, 4), nullable=False),
        sa.Column("multiplier", sa.Numeric(7, 4), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("hours > 0", name="ck_overtime_hours_positive"),
        sa.CheckConstraint("hourly_rate >= 0", name="ck_overtime_rate_non_negative"),
        sa.CheckConstraint("multiplier > 0", name="ck_overtime_multiplier_positive"),
        sa.CheckConstraint("amount >= 0", name="ck_overtime_amount_non_negative"),
        sa.CheckConstraint("status IN ('Draft', 'Approved')", name="ck_overtime_status_valid"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payroll_overtime_inputs_employee_id", "payroll_overtime_inputs", ["employee_id"])
    op.create_index("ix_payroll_overtime_inputs_payroll_period_id", "payroll_overtime_inputs", ["payroll_period_id"])
    op.create_index("ix_overtime_period_employee", "payroll_overtime_inputs", ["payroll_period_id", "employee_id"])

    op.create_table(
        "payroll_one_off_deductions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payroll_period_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("deduction_type", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("allow_partial", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_one_off_deduction_amount_positive"),
        sa.CheckConstraint("priority >= 0", name="ck_one_off_deduction_priority_non_negative"),
        sa.CheckConstraint("status IN ('Draft', 'Approved')", name="ck_one_off_deduction_status_valid"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payroll_one_off_deductions_employee_id", "payroll_one_off_deductions", ["employee_id"])
    op.create_index("ix_payroll_one_off_deductions_payroll_period_id", "payroll_one_off_deductions", ["payroll_period_id"])
    op.create_index("ix_one_off_deduction_period_employee", "payroll_one_off_deductions", ["payroll_period_id", "employee_id"])


def downgrade():
    op.drop_table("payroll_one_off_deductions")
    op.drop_table("payroll_overtime_inputs")
