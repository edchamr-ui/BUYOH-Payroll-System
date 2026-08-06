"""Administrator routes for PAYE tax-band management."""

from decimal import Decimal

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
    StatutoryRuleSet,
    TaxBand,
)
from app.services.audit_log_service import (
    AuditLogService,
)
from app.services.payroll_calculator import (
    PayrollCalculator,
)
from app.services.statutory_rule_service import (
    InvalidTaxBandConfigurationError,
    StatutoryRuleService,
)
from app.settings import settings_bp
from app.settings.statutory_forms import (
    PAYECalculationTestForm,
    TaxBandActionForm,
    TaxBandForm,
)
from app.settings.statutory_helpers import (
    next_tax_band_order,
    ordered_tax_bands,
    percentage_to_rate,
    populate_tax_band_form,
    validate_complete_band_structure,
    validate_tax_band_candidate,
)


@settings_bp.route(
    "/statutory/<int:rule_set_id>/bands",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
@admin_required
def manage_tax_bands(
    rule_set_id,
):
    """Display tax bands and create a new band."""

    rule_set = (
        StatutoryRuleSet.query
        .get_or_404(
            rule_set_id
        )
    )

    tax_band_form = TaxBandForm()
    action_form = TaxBandActionForm()
    calculator_form = (
        PAYECalculationTestForm()
    )

    if request.method == "GET":
        tax_band_form.band_order.data = (
            next_tax_band_order(
                rule_set
            )
        )

        tax_band_form.lower_limit.data = (
            Decimal("0.00")
        )

        tax_band_form.rate_percentage.data = (
            Decimal("0.0000")
        )

    if (
        request.method == "POST"
        and tax_band_form.submit.data
        and tax_band_form.validate_on_submit()
    ):
        lower_limit = Decimal(
            str(
                tax_band_form
                .lower_limit
                .data
            )
        )

        upper_limit = (
            Decimal(
                str(
                    tax_band_form
                    .upper_limit
                    .data
                )
            )
            if tax_band_form.upper_limit.data
            is not None
            else None
        )

        validation_error = (
            validate_tax_band_candidate(
                rule_set=rule_set,
                band_order=(
                    tax_band_form
                    .band_order
                    .data
                ),
                lower_limit=lower_limit,
                upper_limit=upper_limit,
            )
        )

        if validation_error:
            flash(
                validation_error,
                "danger",
            )

        else:
            tax_band = TaxBand(
                rule_set_id=rule_set.id,
                band_order=(
                    tax_band_form
                    .band_order
                    .data
                ),
                lower_limit=lower_limit,
                upper_limit=upper_limit,
                rate=(
                    percentage_to_rate(
                        tax_band_form
                        .rate_percentage
                        .data
                    )
                ),
            )

            db.session.add(
                tax_band
            )

            try:
                db.session.flush()

                AuditLogService.log(
                    user_id=current_user.id,
                    action=(
                        "PAYE Tax Band Created"
                    ),
                    entity_type="TaxBand",
                    entity_id=tax_band.id,
                    description=(
                        "Created PAYE tax band "
                        f"{tax_band.band_order} for "
                        f"{rule_set.display_name}."
                    ),
                    commit=False,
                )

                db.session.commit()

            except IntegrityError:
                db.session.rollback()

                flash(
                    (
                        "The tax band order conflicts "
                        "with an existing band."
                    ),
                    "danger",
                )

            else:
                flash(
                    (
                        "PAYE tax band created "
                        "successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for(
                        "settings.manage_tax_bands",
                        rule_set_id=rule_set.id,
                    )
                )

    valid, message = (
        validate_complete_band_structure(
            rule_set
        )
    )

    return render_template(
        "settings/statutory/bands.html",
        rule_set=rule_set,
        tax_bands=ordered_tax_bands(
            rule_set
        ),
        tax_band_form=tax_band_form,
        action_form=action_form,
        calculator_form=calculator_form,
        calculation_result=None,
        band_structure_valid=valid,
        band_structure_message=message,
        editing_tax_band=None,
    )


@settings_bp.route(
    (
        "/statutory/<int:rule_set_id>/"
        "bands/<int:tax_band_id>/edit"
    ),
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
@admin_required
def edit_tax_band(
    rule_set_id,
    tax_band_id,
):
    """Edit an existing PAYE tax band."""

    rule_set = (
        StatutoryRuleSet.query
        .get_or_404(
            rule_set_id
        )
    )

    tax_band = (
        TaxBand.query
        .filter_by(
            id=tax_band_id,
            rule_set_id=rule_set.id,
        )
        .first_or_404()
    )

    tax_band_form = TaxBandForm()
    action_form = TaxBandActionForm()
    calculator_form = (
        PAYECalculationTestForm()
    )

    if request.method == "GET":
        populate_tax_band_form(
            tax_band_form,
            tax_band,
        )

    if tax_band_form.validate_on_submit():
        lower_limit = Decimal(
            str(
                tax_band_form
                .lower_limit
                .data
            )
        )

        upper_limit = (
            Decimal(
                str(
                    tax_band_form
                    .upper_limit
                    .data
                )
            )
            if tax_band_form.upper_limit.data
            is not None
            else None
        )

        validation_error = (
            validate_tax_band_candidate(
                rule_set=rule_set,
                band_order=(
                    tax_band_form
                    .band_order
                    .data
                ),
                lower_limit=lower_limit,
                upper_limit=upper_limit,
                exclude_tax_band_id=(
                    tax_band.id
                ),
            )
        )

        if validation_error:
            flash(
                validation_error,
                "danger",
            )

        else:
            tax_band.band_order = (
                tax_band_form
                .band_order
                .data
            )

            tax_band.lower_limit = (
                lower_limit
            )

            tax_band.upper_limit = (
                upper_limit
            )

            tax_band.rate = (
                percentage_to_rate(
                    tax_band_form
                    .rate_percentage
                    .data
                )
            )

            try:
                AuditLogService.log(
                    user_id=current_user.id,
                    action=(
                        "PAYE Tax Band Updated"
                    ),
                    entity_type="TaxBand",
                    entity_id=tax_band.id,
                    description=(
                        "Updated PAYE tax band "
                        f"{tax_band.band_order} for "
                        f"{rule_set.display_name}."
                    ),
                    commit=False,
                )

                db.session.commit()

            except IntegrityError:
                db.session.rollback()

                flash(
                    (
                        "The tax band order conflicts "
                        "with an existing band."
                    ),
                    "danger",
                )

            else:
                flash(
                    (
                        "PAYE tax band updated "
                        "successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for(
                        "settings.manage_tax_bands",
                        rule_set_id=rule_set.id,
                    )
                )

    valid, message = (
        validate_complete_band_structure(
            rule_set
        )
    )

    return render_template(
        "settings/statutory/bands.html",
        rule_set=rule_set,
        tax_bands=ordered_tax_bands(
            rule_set
        ),
        tax_band_form=tax_band_form,
        action_form=action_form,
        calculator_form=calculator_form,
        calculation_result=None,
        band_structure_valid=valid,
        band_structure_message=message,
        editing_tax_band=tax_band,
    )


@settings_bp.route(
    (
        "/statutory/<int:rule_set_id>/"
        "bands/<int:tax_band_id>/delete"
    ),
    methods=["POST"],
)
@login_required
@admin_required
def delete_tax_band(
    rule_set_id,
    tax_band_id,
):
    """Delete a PAYE tax band."""

    rule_set = (
        StatutoryRuleSet.query
        .get_or_404(
            rule_set_id
        )
    )

    tax_band = (
        TaxBand.query
        .filter_by(
            id=tax_band_id,
            rule_set_id=rule_set.id,
        )
        .first_or_404()
    )

    form = TaxBandActionForm()

    if not form.validate_on_submit():
        flash(
            (
                "The tax-band deletion request "
                "could not be validated."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "settings.manage_tax_bands",
                rule_set_id=rule_set.id,
            )
        )

    if (
        rule_set.paye_enabled
        and len(rule_set.tax_bands) <= 1
    ):
        flash(
            (
                "Disable PAYE before deleting "
                "its final tax band."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "settings.manage_tax_bands",
                rule_set_id=rule_set.id,
            )
        )

    band_order = tax_band.band_order

    AuditLogService.log(
        user_id=current_user.id,
        action=(
            "PAYE Tax Band Deleted"
        ),
        entity_type="TaxBand",
        entity_id=tax_band.id,
        description=(
            f"Deleted PAYE tax band "
            f"{band_order} from "
            f"{rule_set.display_name}."
        ),
        commit=False,
    )

    db.session.delete(
        tax_band
    )

    db.session.commit()

    valid, message = (
        validate_complete_band_structure(
            rule_set
        )
    )

    if (
        rule_set.paye_enabled
        and not valid
    ):
        rule_set.paye_enabled = False

        AuditLogService.log(
            user_id=current_user.id,
            action=(
                "PAYE Automatically Disabled"
            ),
            entity_type="StatutoryRuleSet",
            entity_id=rule_set.id,
            description=(
                "PAYE was disabled after a tax "
                "band was deleted: "
                f"{message}"
            ),
            commit=False,
        )

        db.session.commit()

        flash(
            (
                "PAYE was automatically disabled "
                "because the remaining tax-band "
                "structure is invalid."
            ),
            "warning",
        )

    flash(
        (
            "PAYE tax band deleted "
            "successfully."
        ),
        "success",
    )

    return redirect(
        url_for(
            "settings.manage_tax_bands",
            rule_set_id=rule_set.id,
        )
    )


@settings_bp.route(
    (
        "/statutory/<int:rule_set_id>/"
        "bands/test"
    ),
    methods=["POST"],
)
@login_required
@admin_required
def test_paye_calculation(
    rule_set_id,
):
    """Test a rule set against a sample monthly salary."""

    rule_set = (
        StatutoryRuleSet.query
        .get_or_404(
            rule_set_id
        )
    )

    tax_band_form = TaxBandForm()
    action_form = TaxBandActionForm()
    calculator_form = (
        PAYECalculationTestForm()
    )

    calculation_result = None

    if calculator_form.validate_on_submit():
        valid, message = (
            validate_complete_band_structure(
                rule_set
            )
        )

        if not valid:
            flash(
                message,
                "danger",
            )

        else:
            original_paye_enabled = (
                rule_set.paye_enabled
            )

            try:
                rule_set.paye_enabled = True

                statutory_config = (
                    StatutoryRuleService
                    .to_configuration(
                        rule_set
                    )
                )

                calculation_result = (
                    PayrollCalculator(
                        basic_salary=(
                            calculator_form
                            .gross_salary
                            .data
                        ),
                        statutory_config=(
                            statutory_config
                        ),
                    )
                    .calculate()
                )

            except (
                InvalidTaxBandConfigurationError,
                ValueError,
            ) as error:
                flash(
                    str(error),
                    "danger",
                )

            finally:
                rule_set.paye_enabled = (
                    original_paye_enabled
                )

                db.session.rollback()

    else:
        for field_errors in (
            calculator_form.errors.values()
        ):
            for error in field_errors:
                flash(
                    error,
                    "danger",
                )

    valid, message = (
        validate_complete_band_structure(
            rule_set
        )
    )

    tax_band_form.band_order.data = (
        next_tax_band_order(
            rule_set
        )
    )

    tax_band_form.lower_limit.data = (
        Decimal("0.00")
    )

    tax_band_form.rate_percentage.data = (
        Decimal("0.0000")
    )

    return render_template(
        "settings/statutory/bands.html",
        rule_set=rule_set,
        tax_bands=ordered_tax_bands(
            rule_set
        ),
        tax_band_form=tax_band_form,
        action_form=action_form,
        calculator_form=calculator_form,
        calculation_result=(
            calculation_result
        ),
        band_structure_valid=valid,
        band_structure_message=message,
        editing_tax_band=None,
    )
