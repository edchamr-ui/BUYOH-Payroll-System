"""add employer payroll costs

Revision ID: 005e4d2bb019
Revises: b25ae7c8d7a3
Create Date: 2026-07-20 20:13:48.072510

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "005e4d2bb019"
down_revision = "b25ae7c8d7a3"
branch_labels = None
depends_on = None


def upgrade():
    """Add employer payroll cost columns."""

    with op.batch_alter_table(
        "payroll_records",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "employer_nssa",
                sa.Numeric(precision=12, scale=2),
                nullable=False,
                server_default="0",
            )
        )

        batch_op.add_column(
            sa.Column(
                "employer_cost",
                sa.Numeric(precision=12, scale=2),
                nullable=False,
                server_default="0",
            )
        )


def downgrade():
    """Remove employer payroll cost columns."""

    with op.batch_alter_table(
        "payroll_records",
        schema=None,
    ) as batch_op:

        batch_op.drop_column("employer_cost")
        batch_op.drop_column("employer_nssa")
