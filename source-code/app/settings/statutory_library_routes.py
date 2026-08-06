"""Administrator routes for the statutory preset library."""

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.auth.permissions import admin_required
from app.models import (
    StatutoryPreset,
    StatutoryRuleSet,
)
from app.services.statutory_library_service import (
    StatutoryLibraryError,
    StatutoryLibraryService,
    StatutoryPresetAlreadyImportedError,
)
from app.settings import settings_bp
from app.settings.statutory_forms import (
    StatutoryPresetImportForm,
)
from app.settings.statutory_helpers import (
    configure_statutory_preset_choices,
)


def _normalise_filter(
    value,
    *,
    default="all",
    uppercase=False,
):
    cleaned = str(value or default).strip()

    if not cleaned:
        cleaned = default

    if uppercase:
        return cleaned.upper()

    return cleaned.lower()


def _imported_rule_lookup():
    """Return installed operational rules keyed by preset key."""

    return {
        rule.source_preset_key: rule
        for rule in (
            StatutoryRuleSet.query
            .filter(
                StatutoryRuleSet.imported_from_library
                .is_(True),
                StatutoryRuleSet.source_preset_key
                .isnot(None),
            )
            .order_by(
                StatutoryRuleSet.imported_at.desc(),
                StatutoryRuleSet.id.desc(),
            )
            .all()
        )
    }


def _available_filter_values():
    published = StatutoryPreset.query.filter(
        StatutoryPreset.is_published.is_(True)
    )

    countries = [
        value
        for (value,) in (
            published
            .with_entities(
                StatutoryPreset.country_name
            )
            .distinct()
            .order_by(
                StatutoryPreset.country_name.asc()
            )
            .all()
        )
    ]

    currencies = [
        value
        for (value,) in (
            published
            .with_entities(
                StatutoryPreset.currency
            )
            .distinct()
            .order_by(
                StatutoryPreset.currency.asc()
            )
            .all()
        )
    ]

    tax_years = [
        value
        for (value,) in (
            published
            .with_entities(
                StatutoryPreset.tax_year
            )
            .distinct()
            .order_by(
                StatutoryPreset.tax_year.desc()
            )
            .all()
        )
    ]

    verification_statuses = [
        value
        for (value,) in (
            published
            .with_entities(
                StatutoryPreset.verification_status
            )
            .distinct()
            .order_by(
                StatutoryPreset.verification_status.asc()
            )
            .all()
        )
    ]

    return {
        "countries": countries,
        "currencies": currencies,
        "tax_years": tax_years,
        "verification_statuses": verification_statuses,
    }


def _filtered_presets():
    search_term = str(
        request.args.get("q", "") or ""
    ).strip()

    country_filter = _normalise_filter(
        request.args.get("country", "all")
    )

    currency_filter = _normalise_filter(
        request.args.get("currency", "all"),
        uppercase=True,
    )

    year_filter = str(
        request.args.get("year", "all") or "all"
    ).strip()

    verification_filter = _normalise_filter(
        request.args.get(
            "verification",
            "all",
        )
    )

    installation_filter = _normalise_filter(
        request.args.get(
            "installation",
            "all",
        )
    )

    query = StatutoryPreset.query.filter(
        StatutoryPreset.is_published.is_(True)
    )

    if search_term:
        like_term = f"%{search_term}%"

        query = query.filter(
            or_(
                StatutoryPreset.name.ilike(like_term),
                StatutoryPreset.country_name.ilike(
                    like_term
                ),
                StatutoryPreset.country_code.ilike(
                    like_term
                ),
                StatutoryPreset.currency.ilike(
                    like_term
                ),
                StatutoryPreset.preset_key.ilike(
                    like_term
                ),
                StatutoryPreset.source_name.ilike(
                    like_term
                ),
            )
        )

    if country_filter != "all":
        query = query.filter(
            StatutoryPreset.country_name.ilike(
                country_filter
            )
        )

    if currency_filter != "ALL":
        query = query.filter(
            StatutoryPreset.currency
            == currency_filter
        )

    if year_filter != "all":
        try:
            tax_year = int(year_filter)
        except ValueError:
            tax_year = None

        if tax_year is not None:
            query = query.filter(
                StatutoryPreset.tax_year == tax_year
            )

    if verification_filter != "all":
        query = query.filter(
            StatutoryPreset.verification_status
            .ilike(verification_filter)
        )

    presets = (
        query.order_by(
            StatutoryPreset.country_name.asc(),
            StatutoryPreset.tax_year.desc(),
            StatutoryPreset.currency.asc(),
            StatutoryPreset.effective_from.desc(),
        ).all()
    )

    imported_rule_sets = _imported_rule_lookup()
    preset_rows = []

    for preset in presets:
        existing_rule = imported_rule_sets.get(
            preset.preset_key
        )

        is_imported = existing_rule is not None

        if (
            installation_filter == "installed"
            and not is_imported
        ):
            continue

        if (
            installation_filter == "available"
            and is_imported
        ):
            continue

        preset_rows.append(
            {
                "preset": preset,
                "existing_rule": existing_rule,
                "is_imported": is_imported,
                "has_update": bool(
                    existing_rule
                    and existing_rule.has_library_update
                ),
            }
        )

    return (
        preset_rows,
        {
            "search_term": search_term,
            "country_filter": country_filter,
            "currency_filter": currency_filter,
            "year_filter": year_filter,
            "verification_filter": (
                verification_filter
            ),
            "installation_filter": (
                installation_filter
            ),
        },
    )


@settings_bp.route("/statutory/library")
@login_required
@admin_required
def statutory_library():
    form = StatutoryPresetImportForm()

    configure_statutory_preset_choices(form)

    preset_rows, filters = _filtered_presets()

    all_published_presets = (
        StatutoryPreset.query
        .filter(
            StatutoryPreset.is_published.is_(True)
        )
        .all()
    )

    imported_rule_sets = _imported_rule_lookup()

    installed_count = sum(
        1
        for preset in all_published_presets
        if preset.preset_key in imported_rule_sets
    )

    available_count = (
        len(all_published_presets)
        - installed_count
    )

    update_count = sum(
        1
        for rule in imported_rule_sets.values()
        if rule.has_library_update
    )

    filter_values = _available_filter_values()

    return render_template(
        "settings/statutory/library.html",
        form=form,
        preset_rows=preset_rows,
        total_presets=len(all_published_presets),
        installed_count=installed_count,
        available_count=available_count,
        update_count=update_count,
        countries=filter_values["countries"],
        currencies=filter_values["currencies"],
        tax_years=filter_values["tax_years"],
        verification_statuses=(
            filter_values[
                "verification_statuses"
            ]
        ),
        **filters,
    )


@settings_bp.route(
    "/statutory/library/import",
    methods=["POST"],
)
@login_required
@admin_required
def import_statutory_preset():
    form = StatutoryPresetImportForm()

    configure_statutory_preset_choices(form)

    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "danger")

        return redirect(
            url_for(
                "settings.statutory_library"
            )
        )

    try:
        result = (
            StatutoryLibraryService.import_preset(
                preset_key=form.preset_key.data,
                imported_by_user_id=(
                    current_user.id
                ),
                activate=bool(
                    form.activate.data
                ),
            )
        )

    except StatutoryPresetAlreadyImportedError as error:
        flash(str(error), "warning")

    except StatutoryLibraryError as error:
        flash(str(error), "danger")

    else:
        flash(
            (
                f"{result.preset.name} was installed "
                f"successfully with "
                f"{result.imported_band_count} PAYE "
                "tax band(s)."
            ),
            "success",
        )

        if not result.rule_set.is_active:
            flash(
                (
                    "The installed rule was saved as "
                    "inactive because another active rule "
                    "overlaps its effective period."
                ),
                "warning",
            )

        return redirect(
            url_for(
                "settings.manage_tax_bands",
                rule_set_id=result.rule_set.id,
            )
        )

    return redirect(
        url_for(
            "settings.statutory_library"
        )
    )
