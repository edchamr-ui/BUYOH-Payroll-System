"""Flask CLI commands for the BUYOH Payroll System."""

import click
from flask import Flask

from app.seeds import seed_statutory_rules
from app.seeds.statutory_rules import StatutoryRuleSeedError


def register_cli_commands(app: Flask):
    """Register application management commands."""

    @app.cli.command("seed-statutory-rules")
    def seed_statutory_rules_command():
        """Create the default statutory payroll configuration."""

        try:
            result = seed_statutory_rules()

        except StatutoryRuleSeedError as error:
            raise click.ClickException(str(error)) from error

        if result["created"]:
            click.secho(
                result["message"],
                fg="green",
            )
        else:
            click.secho(
                result["message"],
                fg="yellow",
            )

    @app.cli.command("seed-all")
    def seed_all_command():
        """Run all required BUYOH database seed operations."""

        try:
            result = seed_statutory_rules()

        except StatutoryRuleSeedError as error:
            raise click.ClickException(str(error)) from error

        if result["created"]:
            click.secho(
                result["message"],
                fg="green",
            )
        else:
            click.secho(
                result["message"],
                fg="yellow",
            )

        click.secho(
            "BUYOH database seeding completed.",
            fg="green",
            bold=True,
        )
