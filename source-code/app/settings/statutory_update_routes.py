"""Administrator routes for reviewing and applying updates."""

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
from app.models import StatutoryRuleSet
from app.services.statutory_transactional_update_service import (
    StatutoryTransactionalUpdateService,
    StatutoryUpdateApplyError,
)
from app.services.statutory_update_difference_service import (
    StatutoryUpdateDifferenceService,
)
from app.services.statutory_update_service import (
    StatutoryUpdateService,
)
from app.settings import settings_bp
from app.settings.statutory_forms import (
    StatutoryActionForm,
)


@settings_bp.route(
    "/statutory/updates",
)
@login_required
@admin_required
def statutory_update_centre():
    """Display installed rules and available statutory updates."""

    summary = StatutoryUpdateService.summary()

    return render_template(
        "settings/statutory/updates.html",
        update_items=summary["items"],
        installed_count=summary["installed_count"],
        update_count=summary["update_count"],
        current_count=summary["current_count"],
        manual_count=summary["manual_count"],
    )


@settings_bp.route(
    "/statutory/updates/<int:rule_set_id>/review",
)
@login_required
@admin_required
def review_statutory_update(rule_set_id):
    """Display a side-by-side statutory update review."""

    rule_set = StatutoryRuleSet.query.get_or_404(
        rule_set_id
    )

    item = StatutoryUpdateService.compare_rule_set(
        rule_set
    )

    if not item.update_available:
        abort(
            404,
            description=(
                "No statutory update is currently "
                "available for this rule set."
            ),
        )

    report = StatutoryUpdateDifferenceService.compare(
        rule_set,
        item.latest_preset,
    )

    action_form = StatutoryActionForm()

    return render_template(
        "settings/statutory/review_update.html",
        item=item,
        rule_set=rule_set,
        latest_preset=item.latest_preset,
        report=report,
        action_form=action_form,
    )


@settings_bp.route(
    "/statutory/updates/<int:rule_set_id>/apply",
    methods=["POST"],
)
@login_required
@admin_required
def apply_statutory_update(rule_set_id):
    """Apply a newer statutory package transactionally."""

    rule_set = StatutoryRuleSet.query.get_or_404(
        rule_set_id
    )

    form = StatutoryActionForm()

    if not form.validate_on_submit():
        flash(
            "The update request could not be validated.",
            "danger",
        )

        return redirect(
            url_for(
                "settings.review_statutory_update",
                rule_set_id=rule_set.id,
            )
        )

    if request.form.get("confirmation") != "APPLY UPDATE":
        flash(
            'Type "APPLY UPDATE" exactly to confirm.',
            "danger",
        )

        return redirect(
            url_for(
                "settings.review_statutory_update",
                rule_set_id=rule_set.id,
            )
        )

    try:
        StatutoryTransactionalUpdateService.apply_update(
            rule_set=rule_set,
            applied_by_user_id=current_user.id,
        )

    except StatutoryUpdateApplyError as error:
        flash(
            str(error),
            "danger",
        )

    else:
        flash(
            (
                "The statutory package was updated successfully. "
                "A rollback snapshot was preserved."
            ),
            "success",
        )

    return redirect(
        url_for(
            "settings.statutory_update_centre"
        )
    )
