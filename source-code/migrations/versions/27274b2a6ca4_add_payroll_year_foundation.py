"""add payroll year foundation

Revision ID: 27274b2a6ca4
Revises: ad9e3cbc2ffb
Create Date: 2026-08-03 19:12:11.683828

"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers used by Alembic.
revision = "27274b2a6ca4"
down_revision = "ad9e3cbc2ffb"
branch_labels = None
depends_on = None


def upgrade():
    """Create payroll years and link existing payroll periods."""

    op.create_table(
        "payroll_years",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "year",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="Open",
            nullable=False,
        ),
        sa.Column(
            "opened_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "opened_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "closing_started_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "closing_started_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "closed_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "closing_reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('Open', 'Closing', 'Closed')",
            name="ck_payroll_year_valid_status",
        ),
        sa.CheckConstraint(
            "year >= 2020 AND year <= 2100",
            name="ck_payroll_year_valid_year",
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["closing_started_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "year",
            name="uq_payroll_year_year",
        ),
    )

    with op.batch_alter_table(
        "payroll_years",
        schema=None,
    ) as batch_op:
        batch_op.create_index(
            batch_op.f(
                "ix_payroll_years_closed_by_user_id"
            ),
            ["closed_by_user_id"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_payroll_years_closing_started_by_user_id"
            ),
            ["closing_started_by_user_id"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_payroll_years_opened_by_user_id"
            ),
            ["opened_by_user_id"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_payroll_years_status"
            ),
            ["status"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_payroll_years_year"
            ),
            ["year"],
            unique=True,
        )

    # Add the foreign-key column as nullable first so legacy rows
    # can be linked safely before enforcing NOT NULL.
    with op.batch_alter_table(
        "payroll_periods",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "payroll_year_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.create_index(
            batch_op.f(
                "ix_payroll_periods_payroll_year_id"
            ),
            ["payroll_year_id"],
            unique=False,
        )

        batch_op.create_unique_constraint(
            "uq_payroll_period_year_month",
            [
                "payroll_year_id",
                "month",
            ],
        )

        batch_op.create_foreign_key(
            "fk_payroll_periods_payroll_year_id",
            "payroll_years",
            ["payroll_year_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Create one parent PayrollYear for every existing legacy year.
    op.execute(
        """
        INSERT INTO payroll_years (
            year,
            status,
            opened_at,
            opened_by_user_id,
            created_at,
            updated_at
        )
        SELECT
            payroll_periods.year,
            'Open',
            MIN(payroll_periods.created_at),
            MIN(payroll_periods.created_by),
            MIN(payroll_periods.created_at),
            MAX(payroll_periods.updated_at)
        FROM payroll_periods
        GROUP BY payroll_periods.year
        ON CONFLICT (year) DO NOTHING
        """
    )

    # Link each existing payroll period to its parent year.
    op.execute(
        """
        UPDATE payroll_periods
        SET payroll_year_id = payroll_years.id
        FROM payroll_years
        WHERE payroll_years.year = payroll_periods.year
        """
    )

    # Enforce the relationship only after backfilling all rows.
    with op.batch_alter_table(
        "payroll_periods",
        schema=None,
    ) as batch_op:
        batch_op.alter_column(
            "payroll_year_id",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade():
    """Remove the payroll-year foundation."""

    with op.batch_alter_table(
        "payroll_periods",
        schema=None,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_payroll_periods_payroll_year_id",
            type_="foreignkey",
        )

        batch_op.drop_constraint(
            "uq_payroll_period_year_month",
            type_="unique",
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_payroll_periods_payroll_year_id"
            )
        )

        batch_op.drop_column(
            "payroll_year_id"
        )

    with op.batch_alter_table(
        "payroll_years",
        schema=None,
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f(
                "ix_payroll_years_year"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_payroll_years_status"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_payroll_years_opened_by_user_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_payroll_years_closing_started_by_user_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_payroll_years_closed_by_user_id"
            )
        )

    op.drop_table(
        "payroll_years"
    )
