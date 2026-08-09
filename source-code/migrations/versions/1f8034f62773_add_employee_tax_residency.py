"""add employee tax residency

Revision ID: 1f8034f62773
Revises: 27274b2a6ca4
Create Date: 2026-08-09 18:16:41.828456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f8034f62773'
down_revision = '27274b2a6ca4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'tax_residency',
                sa.String(length=20),
                server_default='Resident',
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f('ix_employees_tax_residency'),
            ['tax_residency'],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_index(
            batch_op.f('ix_employees_tax_residency')
        )
        batch_op.drop_column('tax_residency')
