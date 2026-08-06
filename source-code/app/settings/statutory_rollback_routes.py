"""Administrator routes for statutory snapshot rollback."""

from flask import (
    abort,
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
    StatutoryRuleSet,
    StatutoryRuleSetVersion,
)
from app.services.statutory_rollback_service import (
    StatutoryRollbackError,
    StatutoryRollbackService,
)
from app.settings import settings_bp
from app.settings.statutory_forms import (
    StatutoryActionForm,
)


def _load_snapshot(rule_set_id, snapshot_id):
    """Load one snapshot and verify that it belongs to the rule set."""

    rule_set = StatutoryRuleSet.query.get_or_404(rule_set_id)

    snapshot = (
        StatutoryRuleSetVersion.query
        .filter_by(
            id=snapshot_id,
            rule_set_id=rule_set.id,
        )
        .first()
    )

    if snapshot is None:
        abort(
            404,
            description=(
                "The selected statutory snapshot "
                "could not be found."
            ),
        )

    return rule_set, snapshot


@settings_bp.route(
    "/statutory/<int:rule_set_id>/history/"
    "<int:snapshot_id>/rollback",
    methods=["GET"],
)
@login_required
@admin_required
def review_statutory_rollback(rule_set_id, snapshot_id):
    """Display the rollback confirmation and comparison screen."""

    rule_set, snapshot = _load_snapshot(
        rule_set_id,
        snapshot_id,
    )

    snapshot_data = dict(snapshot.snapshot_data or {})
    snapshot_bands = list(snapshot_data.get("bands", []))
    action_form = StatutoryActionForm()

    return render_template(
        "settings/statutory/rollback_review.html",
        rule_set=rule_set,
        snapshot=snapshot,
        snapshot_data=snapshot_data,
        snapshot_bands=snapshot_bands,
        action_form=action_form,
    )


@settings_bp.route(
    "/statutory/<int:rule_set_id>/history/"
    "<int:snapshot_id>/rollback/apply",
    methods=["POST"],
)
@login_required
@admin_required
def apply_statutory_rollback(rule_set_id, snapshot_id):
    """Restore a statutory rule from one preserved snapshot."""

    rule_set, snapshot = _load_snapshot(
        rule_set_id,
        snapshot_id,
    )

    form = StatutoryActionForm()

    if not form.validate_on_submit():
        flash(
            "The rollback request could not be validated.",
            "danger",
        )
        return redirect(
            url_for(
                "settings.review_statutory_rollback",
                rule_set_id=rule_set.id,
                snapshot_id=snapshot.id,
            )
        )

    if request.form.get("confirmation") != "ROLLBACK RULE":
        flash(
            'Type "ROLLBACK RULE" exactly to confirm.',
            "danger",
        )
        return redirect(
            url_for(
                "settings.review_statutory_rollback",
                rule_set_id=rule_set.id,
                snapshot_id=snapshot.id,
            )
        )

    try:
        StatutoryRollbackService.rollback(
            rule_set=rule_set,
            snapshot=snapshot,
            rolled_back_by_user_id=current_user.id,
        )

    except StatutoryRollbackError as error:
        flash(str(error), "danger")
        return redirect(
            url_for(
                "settings.review_statutory_rollback",
                rule_set_id=rule_set.id,
                snapshot_id=snapshot.id,
            )
        )

    flash(
        (
            "The statutory rule was rolled back successfully. "
            "The state that existed before rollback was preserved "
            "as a new snapshot."
        ),
        "success",
    )

    return redirect(
        url_for(
            "settings.statutory_version_history",
            rule_set_id=rule_set.id,
        )
    )
