"""Add employee UK tax profiles.

Revision ID: c81b5c8539da
Revises: 3d86fe677782
Create Date: 2026-08-10 14:43:19.619124
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers used by Alembic.
revision = "c81b5c8539da"
down_revision = "3d86fe677782"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "employee_uk_tax_profiles",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "tax_code",
            sa.String(length=20),
            server_default="1257L",
            nullable=False,
        ),
        sa.Column(
            "tax_basis",
            sa.String(length=20),
            server_default="CUMULATIVE",
            nullable=False,
        ),
        sa.Column(
            "tax_region",
            sa.String(length=20),
            server_default="ENGLAND_NI",
            nullable=False,
        ),
        sa.Column(
            "ni_category",
            sa.String(length=2),
            server_default="A",
            nullable=False,
        ),
        sa.Column(
            "is_director",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "director_ni_method",
            sa.String(length=20),
            server_default="STANDARD",
            nullable=False,
        ),
        sa.Column(
            "student_loan_plan",
            sa.String(length=20),
            server_default="NONE",
            nullable=False,
        ),
        sa.Column(
            "postgraduate_loan",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tax_basis IN ('CUMULATIVE', 'W1_M1')",
            name="ck_employee_uk_tax_profiles_tax_basis",
        ),
        sa.CheckConstraint(
            "tax_region IN ('ENGLAND_NI', 'SCOTLAND', 'WALES')",
            name="ck_employee_uk_tax_profiles_tax_region",
        ),
        sa.CheckConstraint(
            "char_length(ni_category) BETWEEN 1 AND 2",
            name="ck_employee_uk_tax_profiles_ni_category_length",
        ),
        sa.CheckConstraint(
            "director_ni_method IN ('STANDARD', 'ALTERNATIVE')",
            name="ck_employee_uk_tax_profiles_director_ni_method",
        ),
        sa.CheckConstraint(
            """
            student_loan_plan IN
            ('NONE', 'PLAN_1', 'PLAN_2', 'PLAN_4', 'PLAN_5')
            """,
            name="ck_employee_uk_tax_profiles_student_loan_plan",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table(
        "employee_uk_tax_profiles",
        schema=None,
    ) as batch_op:
        batch_op.create_index(
            batch_op.f(
                "ix_employee_uk_tax_profiles_employee_id"
            ),
            ["employee_id"],
            unique=True,
        )


def downgrade():
    with op.batch_alter_table(
        "employee_uk_tax_profiles",
        schema=None,
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f(
                "ix_employee_uk_tax_profiles_employee_id"
            )
        )

    op.drop_table("employee_uk_tax_profiles")
