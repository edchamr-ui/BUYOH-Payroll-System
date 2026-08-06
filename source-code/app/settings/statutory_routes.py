"""Administrator routes for operational statutory rule sets."""

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
from sqlalchemy.exc import IntegrityError

from app.auth.permissions import admin_required
from app.extensions import db
from app.models import StatutoryRuleSet
from app.services.audit_log_service import (
    AuditLogService,
)
from app.settings import settings_bp
from app.settings.statutory_forms import (
    StatutoryActionForm,
    StatutoryRuleSetForm,
)
from app.settings.statutory_helpers import (
    find_overlapping_rule,
    percentage_to_rate,
    populate_rule_set_form,
    rule_used_by_payroll,
)


@settings_bp.route(
    "/statutory",
)
@login_required
@admin_required
def statutory_index():
    """Display operational statutory rule sets."""

    currency_filter = request.args.get(
        "currency",
        "all",
    ).strip().upper()

    status_filter = request.args.get(
        "status",
        "all",
    ).strip().lower()

    query = StatutoryRuleSet.query

    if currency_filter != "ALL":
        query = query.filter(
            StatutoryRuleSet.currency
            == currency_filter
        )

    if status_filter == "active":
        query = query.filter(
            StatutoryRuleSet.is_active.is_(
                True
            )
        )

    elif status_filter == "inactive":
        query = query.filter(
            StatutoryRuleSet.is_active.is_(
                False
            )
        )

    rule_sets = (
        query
        .order_by(
            StatutoryRuleSet.currency.asc(),
            StatutoryRuleSet.effective_from.desc(),
            StatutoryRuleSet.id.desc(),
        )
        .all()
    )

    available_currencies = [
        currency
        for (currency,) in (
            StatutoryRuleSet.query
            .with_entities(
                StatutoryRuleSet.currency
            )
            .distinct()
            .order_by(
                StatutoryRuleSet.currency.asc()
            )
            .all()
        )
    ]

    active_count = (
        StatutoryRuleSet.query
        .filter(
            StatutoryRuleSet.is_active.is_(
                True
            )
        )
        .count()
    )

    paye_enabled_count = (
        StatutoryRuleSet.query
        .filter(
            StatutoryRuleSet.paye_enabled.is_(
                True
            )
        )
        .count()
    )

    action_form = (
        StatutoryActionForm()
    )

    return render_template(
        "settings/statutory/index.html",
        rule_sets=rule_sets,
        available_currencies=(
            available_currencies
        ),
        currency_filter=currency_filter,
        status_filter=status_filter,
        total_rule_sets=(
            StatutoryRuleSet.query.count()
        ),
        active_count=active_count,
        paye_enabled_count=(
            paye_enabled_count
        ),
        action_form=action_form,
    )


@settings_bp.route(
    "/statutory/new",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
@admin_required
def create_statutory_rule():
    """Create an operational statutory rule set."""

    form = StatutoryRuleSetForm()

    if form.validate_on_submit():
        currency = (
            form.currency.data
            .strip()
            .upper()
        )

        overlapping_rule = None

        if form.is_active.data:
            overlapping_rule = (
                find_overlapping_rule(
                    currency=currency,
                    effective_from=(
                        form.effective_from.data
                    ),
                    effective_to=(
                        form.effective_to.data
                    ),
                )
            )

        if overlapping_rule is not None:
            flash(
                (
                    "This active rule set overlaps with "
                    f"{overlapping_rule.display_name}. "
                    "Adjust the effective dates or make "
                    "one of the rule sets inactive."
                ),
                "danger",
            )

        else:
            rule_set = StatutoryRuleSet(
                name=(
                    form.name.data.strip()
                ),
                currency=currency,
                effective_from=(
                    form.effective_from.data
                ),
                effective_to=(
                    form.effective_to.data
                ),
                nssa_employee_rate=(
                    percentage_to_rate(
                        form
                        .nssa_employee_percentage
                        .data
                    )
                ),
                nssa_employer_rate=(
                    percentage_to_rate(
                        form
                        .nssa_employer_percentage
                        .data
                    )
                ),
                nssa_monthly_ceiling=(
                    form.nssa_monthly_ceiling.data
                ),
                aids_levy_rate=(
                    percentage_to_rate(
                        form
                        .aids_levy_percentage
                        .data
                    )
                ),
                paye_enabled=False,
                is_active=bool(
                    form.is_active.data
                ),
            )

            requested_paye = bool(
                form.paye_enabled.data
            )

            db.session.add(
                rule_set
            )

            try:
                db.session.flush()

                AuditLogService.log(
                    user_id=current_user.id,
                    action=(
                        "Statutory Rule Set Created"
                    ),
                    entity_type=(
                        "StatutoryRuleSet"
                    ),
                    entity_id=rule_set.id,
                    description=(
                        "Created statutory rule set "
                        f"{rule_set.display_name}."
                    ),
                    commit=False,
                )

                db.session.commit()

            except IntegrityError:
                db.session.rollback()

                flash(
                    (
                        "A statutory rule set with the "
                        "same name, currency and effective "
                        "date already exists."
                    ),
                    "danger",
                )

            else:
                flash(
                    (
                        "Statutory rule set created "
                        "successfully."
                    ),
                    "success",
                )

                if requested_paye:
                    flash(
                        (
                            "PAYE was not enabled yet. "
                            "Add a complete valid PAYE "
                            "tax-band structure first."
                        ),
                        "warning",
                    )

                return redirect(
                    url_for(
                        "settings.statutory_index"
                    )
                )

    return render_template(
        "settings/statutory/form.html",
        form=form,
        page_heading=(
            "Create Statutory Rule Set"
        ),
        page_description=(
            "Create effective-dated payroll "
            "statutory rates for a currency."
        ),
        rule_set=None,
    )


@settings_bp.route(
    "/statutory/<int:rule_set_id>/edit",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
@admin_required
def edit_statutory_rule(
    rule_set_id,
):
    """Update an operational statutory rule set."""

    rule_set = (
        StatutoryRuleSet.query
        .get_or_404(
            rule_set_id
        )
    )

    form = StatutoryRuleSetForm()

    if request.method == "GET":
        populate_rule_set_form(
            form,
            rule_set,
        )

    if form.validate_on_submit():
        currency = (
            form.currency.data
            .strip()
            .upper()
        )

        overlapping_rule = None

        if form.is_active.data:
            overlapping_rule = (
                find_overlapping_rule(
                    currency=currency,
                    effective_from=(
                        form.effective_from.data
                    ),
                    effective_to=(
                        form.effective_to.data
                    ),
                    exclude_rule_set_id=(
                        rule_set.id
                    ),
                )
            )

        if overlapping_rule is not None:
            flash(
                (
                    "This active rule set overlaps with "
                    f"{overlapping_rule.display_name}. "
                    "Adjust the effective dates or "
                    "deactivate one of the rules."
                ),
                "danger",
            )

        elif (
            form.paye_enabled.data
            and not rule_set.tax_bands
        ):
            flash(
                (
                    "PAYE cannot be enabled because "
                    "this rule set has no tax bands."
                ),
                "danger",
            )

        else:
            rule_set.name = (
                form.name.data.strip()
            )

            rule_set.currency = currency

            rule_set.effective_from = (
                form.effective_from.data
            )

            rule_set.effective_to = (
                form.effective_to.data
            )

            rule_set.nssa_employee_rate = (
                percentage_to_rate(
                    form
                    .nssa_employee_percentage
                    .data
                )
            )

            rule_set.nssa_employer_rate = (
                percentage_to_rate(
                    form
                    .nssa_employer_percentage
                    .data
                )
            )

            rule_set.nssa_monthly_ceiling = (
                form.nssa_monthly_ceiling.data
            )

            rule_set.aids_levy_rate = (
                percentage_to_rate(
                    form
                    .aids_levy_percentage
                    .data
                )
            )

            rule_set.paye_enabled = bool(
                form.paye_enabled.data
            )

            rule_set.is_active = bool(
                form.is_active.data
            )

            try:
                AuditLogService.log(
                    user_id=current_user.id,
                    action=(
                        "Statutory Rule Set Updated"
                    ),
                    entity_type=(
                        "StatutoryRuleSet"
                    ),
                    entity_id=rule_set.id,
                    description=(
                        "Updated statutory rule set "
                        f"{rule_set.display_name}."
                    ),
                    commit=False,
                )

                db.session.commit()

            except IntegrityError:
                db.session.rollback()

                flash(
                    (
                        "The statutory rule set could "
                        "not be saved because its name, "
                        "currency and effective date "
                        "conflict with another rule."
                    ),
                    "danger",
                )

            else:
                flash(
                    (
                        "Statutory rule set updated "
                        "successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for(
                        "settings.statutory_index"
                    )
                )

    return render_template(
        "settings/statutory/form.html",
        form=form,
        page_heading=(
            "Edit Statutory Rule Set"
        ),
        page_description=(
            "Update statutory rates and "
            "effective dates."
        ),
        rule_set=rule_set,
    )


@settings_bp.route(
    "/statutory/<int:rule_set_id>/toggle",
    methods=["POST"],
)
@login_required
@admin_required
def toggle_statutory_rule(
    rule_set_id,
):
    """Activate or deactivate an operational rule set."""

    rule_set = (
        StatutoryRuleSet.query
        .get_or_404(
            rule_set_id
        )
    )

    form = StatutoryActionForm()

    if not form.validate_on_submit():
        flash(
            (
                "The statutory rule status request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "settings.statutory_index"
            )
        )

    next_status = (
        not rule_set.is_active
    )

    if next_status:
        overlapping_rule = (
            find_overlapping_rule(
                currency=rule_set.currency,
                effective_from=(
                    rule_set.effective_from
                ),
                effective_to=(
                    rule_set.effective_to
                ),
                exclude_rule_set_id=(
                    rule_set.id
                ),
            )
        )

        if overlapping_rule is not None:
            flash(
                (
                    "This rule set cannot be activated "
                    "because it overlaps with "
                    f"{overlapping_rule.display_name}."
                ),
                "danger",
            )

            return redirect(
                url_for(
                    "settings.statutory_index"
                )
            )

    rule_set.is_active = next_status

    AuditLogService.log(
        user_id=current_user.id,
        action=(
            "Statutory Rule Status Changed"
        ),
        entity_type="StatutoryRuleSet",
        entity_id=rule_set.id,
        description=(
            f"{rule_set.display_name} was "
            f"{'activated' if next_status else 'deactivated'}."
        ),
        commit=False,
    )

    db.session.commit()

    flash(
        (
            f"{rule_set.display_name} "
            f"{'activated' if next_status else 'deactivated'} "
            "successfully."
        ),
        "success",
    )

    return redirect(
        url_for(
            "settings.statutory_index"
        )
    )


@settings_bp.route(
    "/statutory/<int:rule_set_id>/delete",
    methods=["POST"],
)
@login_required
@admin_required
def delete_statutory_rule(
    rule_set_id,
):
    """Delete an unused operational statutory rule set."""

    rule_set = (
        StatutoryRuleSet.query
        .get_or_404(
            rule_set_id
        )
    )

    form = StatutoryActionForm()

    if not form.validate_on_submit():
        flash(
            (
                "The statutory rule deletion request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "settings.statutory_index"
            )
        )

    if rule_used_by_payroll(
        rule_set
    ):
        flash(
            (
                "This rule set cannot be deleted "
                "because payroll records exist within "
                "its effective date range. Deactivate "
                "it instead."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "settings.statutory_index"
            )
        )

    display_name = (
        rule_set.display_name
    )

    AuditLogService.log(
        user_id=current_user.id,
        action=(
            "Statutory Rule Set Deleted"
        ),
        entity_type="StatutoryRuleSet",
        entity_id=rule_set.id,
        description=(
            "Deleted unused statutory rule set "
            f"{display_name}."
        ),
        commit=False,
    )

    db.session.delete(
        rule_set
    )

    db.session.commit()

    flash(
        (
            f"{display_name} deleted "
            "successfully."
        ),
        "success",
    )

    return redirect(
        url_for(
            "settings.statutory_index"
        )
    )
