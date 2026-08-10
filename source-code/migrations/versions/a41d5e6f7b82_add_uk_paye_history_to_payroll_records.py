"""Add UK PAYE history to payroll records.

Revision ID: a41d5e6f7b82
Revises: c81b5c8539da
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa


revision = "a41d5e6f7b82"
down_revision = "c81b5c8539da"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("payroll_records", schema=None) as batch_op:
        batch_op.add_column(sa.Column("uk_tax_code", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("uk_tax_basis", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("uk_tax_region", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("uk_tax_month", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("uk_taxable_pay", sa.Numeric(14, 2), nullable=True))
        batch_op.add_column(sa.Column("uk_prior_taxable_pay", sa.Numeric(14, 2), nullable=True))
        batch_op.add_column(sa.Column("uk_prior_tax_paid", sa.Numeric(14, 2), nullable=True))
        batch_op.create_check_constraint(
            "ck_payroll_record_uk_tax_month_valid",
            "uk_tax_month IS NULL OR (uk_tax_month >= 1 AND uk_tax_month <= 12)",
        )
        batch_op.create_check_constraint(
            "ck_payroll_record_uk_taxable_pay_non_negative",
            "uk_taxable_pay IS NULL OR uk_taxable_pay >= 0",
        )


def downgrade():
    with op.batch_alter_table("payroll_records", schema=None) as batch_op:
        batch_op.drop_constraint("ck_payroll_record_uk_taxable_pay_non_negative", type_="check")
        batch_op.drop_constraint("ck_payroll_record_uk_tax_month_valid", type_="check")
        batch_op.drop_column("uk_prior_tax_paid")
        batch_op.drop_column("uk_prior_taxable_pay")
        batch_op.drop_column("uk_taxable_pay")
        batch_op.drop_column("uk_tax_month")
        batch_op.drop_column("uk_tax_region")
        batch_op.drop_column("uk_tax_basis")
        batch_op.drop_column("uk_tax_code")
