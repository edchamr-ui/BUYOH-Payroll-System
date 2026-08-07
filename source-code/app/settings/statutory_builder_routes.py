"""Administrator routes for building statutory packages."""

from datetime import date

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
from app.models import StatutoryPreset
from app.services.audit_log_service import (
    AuditLogService,
)
from app.settings import settings_bp
from app.settings.statutory_builder_forms import (
    StatutoryPackageStepOneForm,
)


def _normalise_package_form(
    form,
):
    """Normalize statutory package identity fields."""

    form.country_code.data = (
        str(
            form.country_code.data
            or ""
        )
        .strip()
        .upper()
    )

    form.country_name.data = (
        str(
            form.country_name.data
            or ""
        )
        .strip()
    )

    form.country_flag.data = (
        str(
            form.country_flag.data
            or ""
        )
        .strip()
        or None
    )

    form.currency.data = (
        str(
            form.currency.data
            or ""
        )
        .strip()
        .upper()
    )

    form.package_name.data = (
        str(
            form.package_name.data
            or ""
        )
        .strip()
    )

    form.preset_key.data = (
        str(
            form.preset_key.data
            or ""
        )
        .strip()
        .upper()
    )

    form.engine_type.data = (
        str(
            form.engine_type.data
            or ""
        )
        .strip()
        .upper()
    )

    form.version.data = (
        str(
            form.version.data
            or "1.0"
        )
        .strip()
    )


def _populate_identity_form(
    form,
    package,
):
    """Populate Step 1 from an existing statutory package."""

    form.country_code.data = package.country_code
    form.country_name.data = package.country_name
    form.country_flag.data = package.country_flag
    form.currency.data = package.currency
    form.tax_year.data = package.tax_year
    form.tax_period_label.data = (
        package.tax_period_label
        or "Monthly"
    )
    form.package_name.data = package.name
    form.preset_key.data = package.preset_key
    form.engine_type.data = package.engine_type
    form.version.data = package.version
    form.effective_from.data = package.effective_from
    form.effective_to.data = package.effective_to
    form.paye_enabled.data = package.paye_enabled


def _identity_conflict_exists(
    form,
    *,
    exclude_id=None,
):
    """Return another package with the protected identity."""

    query = StatutoryPreset.query.filter(
        StatutoryPreset.country_code
        == form.country_code.data,
        StatutoryPreset.currency
        == form.currency.data,
        StatutoryPreset.tax_year
        == form.tax_year.data,
        StatutoryPreset.effective_from
        == form.effective_from.data,
        StatutoryPreset.version
        == form.version.data,
    )

    if exclude_id is not None:
        query = query.filter(
            StatutoryPreset.id != exclude_id
        )

    return query.first()


@settings_bp.route(
    "/statutory/builder",
)
@login_required
@admin_required
def statutory_package_builder():
    """Display the Statutory Package Studio."""

    packages = (
        StatutoryPreset.query
        .order_by(
            StatutoryPreset.supports_payroll.desc(),
            StatutoryPreset.is_published.asc(),
            StatutoryPreset.country_name.asc(),
            StatutoryPreset.tax_year.desc(),
            StatutoryPreset.currency.asc(),
            StatutoryPreset.updated_at.desc(),
            StatutoryPreset.id.desc(),
        )
        .all()
    )

    draft_count = sum(
        1
        for package in packages
        if not package.is_published
    )

    published_count = sum(
        1
        for package in packages
        if package.is_published
    )

    payroll_ready_count = sum(
        1
        for package in packages
        if package.supports_payroll
    )

    incomplete_count = sum(
        1
        for package in packages
        if not package.supports_payroll
    )

    return render_template(
        "settings/statutory/builder/index.html",
        packages=packages,
        draft_count=draft_count,
        published_count=published_count,
        payroll_ready_count=payroll_ready_count,
        incomplete_count=incomplete_count,
        total_packages=len(packages),
    )


@settings_bp.route(
    "/statutory/builder/new",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
@admin_required
def create_statutory_package():
    """Create the first stage of a statutory package draft."""

    form = StatutoryPackageStepOneForm()

    if request.method == "GET":
        current_year = date.today().year

        form.tax_year.data = current_year

        form.effective_from.data = date(
            current_year,
            1,
            1,
        )

        form.effective_to.data = date(
            current_year,
            12,
            31,
        )

    if form.validate_on_submit():
        _normalise_package_form(
            form
        )

        existing_package = (
            StatutoryPreset.query
            .filter_by(
                preset_key=form.preset_key.data
            )
            .first()
        )

        if existing_package is not None:
            flash(
                (
                    "A statutory package already uses preset key "
                    f"{form.preset_key.data}."
                ),
                "danger",
            )

            return render_template(
                "settings/statutory/builder/wizard_step1.html",
                form=form,
                package=None,
                editing=False,
            )

        identity_conflict = (
            _identity_conflict_exists(form)
        )

        if identity_conflict is not None:
            flash(
                (
                    "A statutory package already exists for "
                    f"{form.country_code.data} / "
                    f"{form.currency.data} / "
                    f"{form.tax_year.data}, effective "
                    f"{form.effective_from.data:%d %b %Y}, "
                    f"version {form.version.data}. "
                    "Continue that package or use a different version."
                ),
                "danger",
            )

            return render_template(
                "settings/statutory/builder/wizard_step1.html",
                form=form,
                package=None,
                editing=False,
            )

        package = StatutoryPreset(
            preset_key=form.preset_key.data,
            country_code=form.country_code.data,
            country_name=form.country_name.data,
            country_flag=form.country_flag.data,
            currency=form.currency.data,
            tax_year=form.tax_year.data,
            tax_period_label=(
                form.tax_period_label.data
            ),
            version=form.version.data,
            name=form.package_name.data,
            engine_type=form.engine_type.data,
            effective_from=form.effective_from.data,
            effective_to=form.effective_to.data,
            verification_status="Draft",
            source_name="Pending official source",
            source_description=(
                "Official statutory source information "
                "will be completed during Step 4."
            ),
            source_reference=None,
            official_source_url=None,
            last_verified_at=None,
            paye_enabled=bool(
                form.paye_enabled.data
            ),
            employee_contribution_name=None,
            employee_contribution_rate=0,
            employer_contribution_name=None,
            employer_contribution_rate=0,
            contribution_ceiling=0,
            levy_name=None,
            levy_rate=0,
            supports_import=False,
            supports_payroll=False,
            is_published=False,
            is_locked=False,
            notes=(
                "Draft package created through the "
                "Statutory Package Studio."
            ),
        )

        db.session.add(
            package
        )

        try:
            db.session.flush()

            AuditLogService.log(
                user_id=current_user.id,
                action=(
                    "Statutory Package Draft Created"
                ),
                entity_type="StatutoryPreset",
                entity_id=package.id,
                description=(
                    "Created statutory package draft "
                    f"{package.name} "
                    f"({package.preset_key})."
                ),
                commit=False,
            )

            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                (
                    "The statutory package could not be "
                    "created because one of its identifiers "
                    "already exists."
                ),
                "danger",
            )

        else:
            flash(
                (
                    f"{package.name} was created as a draft. "
                    "Contribution configuration is the next step."
                ),
                "success",
            )

            return redirect(
                url_for(
                    "settings.continue_statutory_package",
                    preset_id=package.id,
                )
            )

    return render_template(
        "settings/statutory/builder/wizard_step1.html",
        form=form,
        package=None,
        editing=False,
    )


@settings_bp.route(
    "/statutory/builder/<int:preset_id>/continue",
)
@login_required
@admin_required
def continue_statutory_package(
    preset_id,
):
    """Continue building an existing statutory package."""

    package = (
        StatutoryPreset.query
        .get_or_404(preset_id)
    )

    if (
        package.is_locked
        and package.supports_payroll
    ):
        flash(
            (
                "This package is locked and payroll-ready. "
                "Create a new package version before modifying it."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "settings.statutory_package_builder"
            )
        )

    return redirect(
        url_for(
            "settings.edit_statutory_package_identity",
            preset_id=package.id,
        )
    )


@settings_bp.route(
    "/statutory/builder/<int:preset_id>/identity",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
@admin_required
def edit_statutory_package_identity(
    preset_id,
):
    """Edit Step 1 identity details for an existing package."""

    package = (
        StatutoryPreset.query
        .get_or_404(preset_id)
    )

    if (
        package.is_locked
        and package.supports_payroll
    ):
        flash(
            (
                "This payroll-ready package is locked. "
                "Create a new version before editing it."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "settings.statutory_package_builder"
            )
        )

    form = StatutoryPackageStepOneForm()

    if request.method == "GET":
        _populate_identity_form(
            form,
            package,
        )

    if form.validate_on_submit():
        _normalise_package_form(form)

        duplicate_key = (
            StatutoryPreset.query
            .filter(
                StatutoryPreset.preset_key
                == form.preset_key.data,
                StatutoryPreset.id
                != package.id,
            )
            .first()
        )

        if duplicate_key is not None:
            flash(
                (
                    "Another package already uses preset key "
                    f"{form.preset_key.data}."
                ),
                "danger",
            )

        else:
            identity_conflict = (
                _identity_conflict_exists(
                    form,
                    exclude_id=package.id,
                )
            )

            if identity_conflict is not None:
                flash(
                    (
                        "Another package already uses this country, "
                        "currency, tax year, effective date and "
                        "version combination."
                    ),
                    "danger",
                )

            else:
                package.country_code = (
                    form.country_code.data
                )
                package.country_name = (
                    form.country_name.data
                )
                package.country_flag = (
                    form.country_flag.data
                )
                package.currency = (
                    form.currency.data
                )
                package.tax_year = (
                    form.tax_year.data
                )
                package.tax_period_label = (
                    form.tax_period_label.data
                )
                package.name = (
                    form.package_name.data
                )
                package.preset_key = (
                    form.preset_key.data
                )
                package.engine_type = (
                    form.engine_type.data
                )
                package.version = (
                    form.version.data
                )
                package.effective_from = (
                    form.effective_from.data
                )
                package.effective_to = (
                    form.effective_to.data
                )
                package.paye_enabled = bool(
                    form.paye_enabled.data
                )

                package.supports_import = False
                package.supports_payroll = False

                if (
                    package.verification_status
                    == "Verified"
                ):
                    package.verification_status = (
                        "Draft"
                    )

                try:
                    AuditLogService.log(
                        user_id=current_user.id,
                        action=(
                            "Statutory Package Identity Updated"
                        ),
                        entity_type="StatutoryPreset",
                        entity_id=package.id,
                        description=(
                            "Updated Step 1 identity for "
                            f"{package.name} "
                            f"({package.preset_key})."
                        ),
                        commit=False,
                    )

                    db.session.commit()

                except IntegrityError:
                    db.session.rollback()

                    flash(
                        (
                            "The package identity conflicts with "
                            "another statutory package."
                        ),
                        "danger",
                    )

                else:
                    flash(
                        (
                            "Package information saved. "
                            "Contribution configuration is next."
                        ),
                        "success",
                    )

                    return redirect(
                        url_for(
                            "settings.statutory_package_builder"
                        )
                    )

    return render_template(
        "settings/statutory/builder/wizard_step1.html",
        form=form,
        package=package,
        editing=True,
    )
