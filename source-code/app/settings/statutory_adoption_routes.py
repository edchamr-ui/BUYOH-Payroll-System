"""Administrator routes for adopting legacy statutory rules."""

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)

from app.auth.permissions import admin_required
from app.models import (
    StatutoryPreset,
    StatutoryRuleSet,
)
from app.services.statutory_adoption_service import (
    StatutoryAdoptionError,
    StatutoryAdoptionService,
)
from app.settings import settings_bp
from app.settings.statutory_forms import StatutoryActionForm


@settings_bp.route(
    "/statutory/<int:rule_set_id>/adopt",
    methods=["GET", "POST"],
)
@login_required
@admin_required
def adopt_statutory_rule(
    rule_set_id,
):
    """Compare and link a legacy operational rule to a preset."""

    action_form = StatutoryActionForm()

    rule_set = (
        StatutoryRuleSet.query
        .get_or_404(rule_set_id)
    )

    presets = (
        StatutoryPreset.query
        .filter(
            StatutoryPreset.is_published.is_(True),
            StatutoryPreset.supports_import.is_(True),
            StatutoryPreset.supports_payroll.is_(True),
            StatutoryPreset.currency
            == rule_set.currency,
        )
        .order_by(
            StatutoryPreset.effective_from.desc(),
            StatutoryPreset.version.desc(),
        )
        .all()
    )

    selected_key = str(
        request.values.get(
            "preset_key",
            "",
        )
        or ""
    ).strip()

    selected_preset = None
    comparison = None

    if selected_key:
        selected_preset = (
            StatutoryPreset.query
            .filter_by(
                preset_key=selected_key,
                is_published=True,
            )
            .first_or_404()
        )

        comparison = (
            StatutoryAdoptionService.compare(
                rule_set,
                selected_preset,
            )
        )

    if request.method == "POST":
        if not action_form.validate_on_submit():
            flash(
                "The adoption request could not be validated.",
                "danger",
            )
            return redirect(
                url_for(
                    "settings.adopt_statutory_rule",
                    rule_set_id=rule_set.id,
                    preset_key=selected_key,
                )
            )

        if (
            selected_preset is None
            or comparison is None
        ):
            flash(
                "Select a statutory preset first.",
                "danger",
            )

        elif not comparison.compatible:
            flash(
                "The operational rule does not exactly "
                "match the selected preset.",
                "danger",
            )

        elif request.form.get("confirmation") != "LINK RULE":
            flash(
                'Type "LINK RULE" exactly to confirm.',
                "danger",
            )

        else:
            try:
                StatutoryAdoptionService.adopt(
                    rule_set=rule_set,
                    preset=selected_preset,
                    adopted_by_user_id=(
                        current_user.id
                    ),
                )

            except StatutoryAdoptionError as error:
                flash(
                    str(error),
                    "danger",
                )

            else:
                flash(
                    (
                        f"{rule_set.display_name} is now "
                        f"linked to "
                        f"{selected_preset.display_name}."
                    ),
                    "success",
                )

                return redirect(
                    url_for(
                        "settings.statutory_update_centre"
                    )
                )

    return render_template(
        "settings/statutory/adopt.html",
        rule_set=rule_set,
        presets=presets,
        selected_preset=selected_preset,
        selected_key=selected_key,
        comparison=comparison,
        action_form=action_form,
    )

