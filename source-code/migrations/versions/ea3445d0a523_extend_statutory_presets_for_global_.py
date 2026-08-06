"""extend statutory presets for global library

Revision ID: ea3445d0a523
Revises: c7046d0fd66c
Create Date: 2026-08-02

"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers used by Alembic.
revision = "ea3445d0a523"
down_revision = "c7046d0fd66c"
branch_labels = None
depends_on = None


def upgrade():
    """
    Extend statutory presets for the global library.

    Temporary server defaults populate existing rows safely.
    The defaults are removed after the migration so application
    defaults remain controlled by the SQLAlchemy model.
    """

    with op.batch_alter_table(
        "statutory_presets",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "country_flag",
                sa.String(length=16),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "tax_period_label",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "version",
                sa.String(length=50),
                nullable=False,
                server_default=sa.text("'1.0'"),
            )
        )

        batch_op.add_column(
            sa.Column(
                "engine_type",
                sa.String(length=80),
                nullable=False,
                server_default=sa.text(
                    "'ZIMBABWE_PROGRESSIVE'"
                ),
            )
        )

        batch_op.add_column(
            sa.Column(
                "official_source_url",
                sa.String(length=1000),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "last_verified_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "notes",
                sa.Text(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "supports_import",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

        batch_op.add_column(
            sa.Column(
                "supports_payroll",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_presets_engine_type"
            ),
            [
                "engine_type",
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_presets_supports_import"
            ),
            [
                "supports_import",
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_presets_supports_payroll"
            ),
            [
                "supports_payroll",
            ],
            unique=False,
        )

        # Replace the previous uniqueness rule so multiple
        # versions of the same statutory period can coexist.
        batch_op.drop_constraint(
            "uq_statutory_preset_country_currency_year",
            type_="unique",
        )

        batch_op.create_unique_constraint(
            "uq_statutory_preset_country_currency_year",
            [
                "country_code",
                "currency",
                "tax_year",
                "effective_from",
                "version",
            ],
        )

    # Explicitly mark the existing Zimbabwe preset as supported.
    op.execute(
        """
        UPDATE statutory_presets
        SET
            country_flag = '🇿🇼',
            tax_period_label = '2025',
            version = '1.0',
            engine_type = 'ZIMBABWE_PROGRESSIVE',
            supports_import = TRUE,
            supports_payroll = TRUE
        WHERE preset_key = 'ZW_USD_2025_MONTHLY'
        """
    )

    # Remove migration-only database defaults. New records will
    # use the defaults defined by the SQLAlchemy model.
    with op.batch_alter_table(
        "statutory_presets",
        schema=None,
    ) as batch_op:

        batch_op.alter_column(
            "version",
            existing_type=sa.String(length=50),
            nullable=False,
            server_default=None,
        )

        batch_op.alter_column(
            "engine_type",
            existing_type=sa.String(length=80),
            nullable=False,
            server_default=None,
        )

        batch_op.alter_column(
            "supports_import",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None,
        )

        batch_op.alter_column(
            "supports_payroll",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None,
        )


def downgrade():
    """Remove global statutory-library fields."""

    with op.batch_alter_table(
        "statutory_presets",
        schema=None,
    ) as batch_op:

        batch_op.drop_constraint(
            "uq_statutory_preset_country_currency_year",
            type_="unique",
        )

        batch_op.create_unique_constraint(
            "uq_statutory_preset_country_currency_year",
            [
                "country_code",
                "currency",
                "tax_year",
                "effective_from",
            ],
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_presets_supports_payroll"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_presets_supports_import"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_presets_engine_type"
            )
        )

        batch_op.drop_column(
            "supports_payroll"
        )

        batch_op.drop_column(
            "supports_import"
        )

        batch_op.drop_column(
            "notes"
        )

        batch_op.drop_column(
            "last_verified_at"
        )

        batch_op.drop_column(
            "official_source_url"
        )

        batch_op.drop_column(
            "engine_type"
        )

        batch_op.drop_column(
            "version"
        )

        batch_op.drop_column(
            "tax_period_label"
        )

        batch_op.drop_column(
            "country_flag"
        )
