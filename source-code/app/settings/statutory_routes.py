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
from app.models import (
    StatutoryPreset,
    StatutoryRuleSet,
)
from app.services.audit_log_service import (
    AuditLogService,
)
from app.services.statutory_engines import (
    StatutoryEngineRegistry,
    StatutoryEngineRegistryError,
)
from app.services.statutory_rule_service import (
    StatutoryRuleService,
    StatutoryRuleServiceError,
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


def _friendly_engine_name(engine_key):
    labels = {
        "ZIMBABWE_PROGRESSIVE": "Progressive PAYE",
        "ZAMBIA_PROGRESSIVE": "Progressive PAYE",
        "BOTSWANA_PAYE": "Botswana PAYE",
        "NAMIBIA_ANNUAL": "Namibia Annual Tax",
        "SOUTH_AFRICA_REBATE": "PAYE with Rebates",
        "KENYA_RELIEF": "PAYE with Reliefs",
    }
    key = str(engine_key or "").strip().upper()
    return labels.get(key, key.replace("_", " ").title() or "Not configured")


def _installed_rule_lookup():
    return {
        rule.source_preset_key: rule
        for rule in (
            StatutoryRuleSet.query
            .filter(
                StatutoryRuleSet.imported_from_library.is_(True),
                StatutoryRuleSet.source_preset_key.isnot(None),
            )
            .order_by(
                StatutoryRuleSet.imported_at.desc(),
                StatutoryRuleSet.id.desc(),
            )
            .all()
        )
    }


def _build_engine_dashboard_rows():
    presets = (
        StatutoryPreset.query
        .filter(StatutoryPreset.is_published.is_(True))
        .order_by(
            StatutoryPreset.country_name.asc(),
            StatutoryPreset.tax_year.desc(),
            StatutoryPreset.currency.asc(),
        )
        .all()
    )
    installed = _installed_rule_lookup()
    rows = []

    for preset in presets:
        rule = installed.get(preset.preset_key)
        engine_registered = False
        engine_class_name = None
        configuration_valid = False
        validation_errors = ()
        validation_warnings = ()

        try:
            engine = StatutoryEngineRegistry.resolve(preset.engine_type)
        except StatutoryEngineRegistryError as error:
            validation_errors = (str(error),)
        else:
            engine_registered = True
            engine_class_name = type(engine).__name__
            if rule is not None:
                try:
                    config = StatutoryRuleService.to_configuration(rule)
                    validation = engine.validate_configuration(config)
                except (StatutoryRuleServiceError, ValueError, TypeError) as error:
                    validation_errors = (str(error),)
                else:
                    configuration_valid = validation.valid
                    validation_errors = validation.errors
                    validation_warnings = validation.warnings

        verified = str(preset.verification_status or '').strip().lower() == 'verified'
        bands = list(preset.bands or [])
        tax_bands_valid = bool(
            (not preset.paye_enabled)
            or (bands and bands[0].lower_limit == 0 and bands[-1].upper_limit is None)
        )
        payroll_ready = bool(
            preset.supports_payroll
            and verified
            and engine_registered
            and tax_bands_valid
            and (rule is None or configuration_valid)
        )

        rows.append({
            'preset': preset,
            'rule_set': rule,
            'country_flag': preset.country_flag or '🌐',
            'country_name': preset.country_name,
            'country_code': preset.country_code,
            'currency': preset.currency,
            'engine_name': _friendly_engine_name(preset.engine_type),
            'engine_class_name': engine_class_name,
            'engine_registered': engine_registered,
            'tax_year': preset.tax_year,
            'version': preset.version,
            'verified': verified,
            'tax_bands_valid': tax_bands_valid,
            'configuration_valid': configuration_valid,
            'payroll_ready': payroll_ready,
            'validation_errors': validation_errors,
            'validation_warnings': validation_warnings,
        })

    return rows


@settings_bp.route(
    "/statutory",
)
@login_required
@admin_required
def statutory_index():
    """Display the enterprise statutory engine dashboard."""

    currency_filter = request.args.get("currency", "all").strip().upper()
    status_filter = request.args.get("status", "all").strip().lower()
    readiness_filter = request.args.get("readiness", "all").strip().lower()
    search_term = request.args.get("q", "").strip().lower()

    all_rows = _build_engine_dashboard_rows()
    engine_rows = []

    for row in all_rows:
        rule = row["rule_set"]

        if currency_filter != "ALL" and row["currency"] != currency_filter:
            continue
        if status_filter == "installed" and rule is None:
            continue
        if status_filter == "catalogue" and rule is not None:
            continue
        if status_filter == "active" and not (rule and rule.is_active):
            continue
        if status_filter == "inactive" and not (rule and not rule.is_active):
            continue
        if readiness_filter == "ready" and not row["payroll_ready"]:
            continue
        if readiness_filter == "pending" and row["payroll_ready"]:
            continue

        if search_term:
            haystack = " ".join([
                row["country_name"],
                row["country_code"],
                row["currency"],
                row["engine_name"],
                str(row["tax_year"]),
                str(row["version"]),
                row["preset"].name,
            ]).lower()
            if search_term not in haystack:
                continue

        engine_rows.append(row)

    action_form = StatutoryActionForm()

    return render_template(
        "settings/statutory/index.html",
        engine_rows=engine_rows,
        supported_countries=len({row["country_code"] for row in all_rows}),
        total_packages=len(all_rows),
        registered_engine_count=sum(row["engine_registered"] for row in all_rows),
        installed_count=sum(row["rule_set"] is not None for row in all_rows),
        active_count=sum(bool(row["rule_set"] and row["rule_set"].is_active) for row in all_rows),
        payroll_ready_count=sum(row["payroll_ready"] for row in all_rows),
        pending_count=sum(not row["payroll_ready"] for row in all_rows),
        available_currencies=sorted({row["currency"] for row in all_rows}),
        currency_filter=currency_filter,
        status_filter=status_filter,
        readiness_filter=readiness_filter,
        search_term=search_term,
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
