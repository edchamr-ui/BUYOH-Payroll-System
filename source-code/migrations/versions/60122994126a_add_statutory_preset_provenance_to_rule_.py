"""add statutory preset provenance to rule sets

Revision ID: 60122994126a
Revises: ea3445d0a523
Create Date: 2026-08-02

"""

from alembic import op
import sqlalchemy as sa


revision = "60122994126a"
down_revision = "ea3445d0a523"
branch_labels = None
depends_on = None


def upgrade():
    """Add statutory-library provenance to operational rule sets."""

    with op.batch_alter_table(
        "statutory_rule_sets",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "source_preset_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "source_preset_key",
                sa.String(length=120),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "source_preset_version",
                sa.String(length=50),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "source_engine_type",
                sa.String(length=80),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "source_country_code",
                sa.String(length=2),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "imported_from_library",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

        batch_op.add_column(
            sa.Column(
                "imported_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "imported_by_user_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_rule_sets_source_preset_id"
            ),
            ["source_preset_id"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_rule_sets_source_preset_key"
            ),
            ["source_preset_key"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_rule_sets_source_engine_type"
            ),
            ["source_engine_type"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_rule_sets_source_country_code"
            ),
            ["source_country_code"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_rule_sets_imported_from_library"
            ),
            ["imported_from_library"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_statutory_rule_sets_imported_by_user_id"
            ),
            ["imported_by_user_id"],
            unique=False,
        )

        batch_op.create_foreign_key(
            "fk_statutory_rule_sets_source_preset_id",
            "statutory_presets",
            ["source_preset_id"],
            ["id"],
            ondelete="SET NULL",
        )

        batch_op.create_foreign_key(
            "fk_statutory_rule_sets_imported_by_user_id",
            "users",
            ["imported_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Existing operational rules were created manually or before
    # provenance tracking existed, so mark them as not imported.
    op.execute(
        """
        UPDATE statutory_rule_sets
        SET imported_from_library = FALSE
        WHERE imported_from_library IS NULL
        """
    )

    # Remove the migration-only database default. Future inserts
    # use the SQLAlchemy model default.
    with op.batch_alter_table(
        "statutory_rule_sets",
        schema=None,
    ) as batch_op:

        batch_op.alter_column(
            "imported_from_library",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None,
        )


def downgrade():
    """Remove statutory-library provenance fields."""

    with op.batch_alter_table(
        "statutory_rule_sets",
        schema=None,
    ) as batch_op:

        batch_op.drop_constraint(
            "fk_statutory_rule_sets_imported_by_user_id",
            type_="foreignkey",
        )

        batch_op.drop_constraint(
            "fk_statutory_rule_sets_source_preset_id",
            type_="foreignkey",
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_rule_sets_imported_by_user_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_rule_sets_imported_from_library"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_rule_sets_source_country_code"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_rule_sets_source_engine_type"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_rule_sets_source_preset_key"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_statutory_rule_sets_source_preset_id"
            )
        )

        batch_op.drop_column(
            "imported_by_user_id"
        )

        batch_op.drop_column(
            "imported_at"
        )

        batch_op.drop_column(
            "imported_from_library"
        )

        batch_op.drop_column(
            "source_country_code"
        )

        batch_op.drop_column(
            "source_engine_type"
        )

        batch_op.drop_column(
            "source_preset_version"
        )

        batch_op.drop_column(
            "source_preset_key"
        )

        batch_op.drop_column(
            "source_preset_id"
        )
