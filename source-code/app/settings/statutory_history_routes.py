"""Administrator routes for statutory version history."""

from flask import render_template
from flask_login import login_required

from app.auth.permissions import admin_required
from app.models import StatutoryRuleSet
from app.services.statutory_version_history_service import (
    StatutoryVersionHistoryService,
)
from app.settings import settings_bp
from app.settings.statutory_forms import (
    StatutoryActionForm,
)


@settings_bp.route(
    "/statutory/<int:rule_set_id>/history",
)
@login_required
@admin_required
def statutory_version_history(rule_set_id):
    """Display read-only version history for one rule set."""

    rule_set = StatutoryRuleSet.query.get_or_404(
        rule_set_id
    )

    summary = (
        StatutoryVersionHistoryService
        .summary_for_rule_set(
            rule_set
        )
    )

    action_form = StatutoryActionForm()

    return render_template(
        "settings/statutory/history.html",
        rule_set=summary["rule_set"],
        history_items=summary["items"],
        snapshot_count=summary[
            "snapshot_count"
        ],
        latest_snapshot=summary[
            "latest_snapshot"
        ],
        current_version=summary[
            "current_version"
        ],
        action_form=action_form,
    )
