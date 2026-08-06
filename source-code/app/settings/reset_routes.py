"""Administrator routes for the payroll reset centre."""

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.auth.permissions import admin_required
from app.services.payroll_reset_service import (
    PayrollResetError,
    PayrollResetService,
)
from app.settings import settings_bp
from app.settings.reset_forms import (
    PayrollConfigurationResetForm,
    PayrollFactoryResetForm,
    PayrollHistoryResetForm,
)


def _password_is_valid(form):
    """Verify the signed-in administrator's current password."""

    return current_user.check_password(
        form.current_password.data
    )


def _flash_form_errors(form):
    """Display reset-form validation errors."""

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, "danger")


def _flash_reset_result(
    *,
    result,
    success_message,
):
    """Display a reset completion summary."""

    deleted_total = sum(
        result.deleted_counts.values()
    )

    flash(
        (
            f"{success_message} "
            f"{deleted_total} database record(s) were removed."
        ),
        "success",
    )

    if result.removed_files:
        flash(
            (
                f"{result.removed_files} generated payroll "
                "file(s) were removed."
            ),
            "info",
        )

    if result.file_warnings:
        flash(
            (
                "The database reset completed, but some generated "
                "files could not be removed."
            ),
            "warning",
        )


@settings_bp.route("/payroll-reset")
@login_required
@admin_required
def payroll_reset_index():
    """Display reset levels and confirmation modals."""

    return render_template(
        "settings/reset/index.html",
        preview=PayrollResetService.preview(),
        history_form=PayrollHistoryResetForm(
            prefix="history"
        ),
        configuration_form=PayrollConfigurationResetForm(
            prefix="configuration"
        ),
        factory_form=PayrollFactoryResetForm(
            prefix="factory"
        ),
    )


@settings_bp.route(
    "/payroll-reset/history",
    methods=["POST"],
)
@login_required
@admin_required
def reset_payroll_history():
    """Delete payroll history while preserving periods."""

    form = PayrollHistoryResetForm(
        prefix="history"
    )

    if not form.validate_on_submit():
        _flash_form_errors(form)

        return redirect(
            url_for("settings.payroll_reset_index")
        )

    if not _password_is_valid(form):
        flash(
            "The administrator password is incorrect.",
            "danger",
        )

        return redirect(
            url_for("settings.payroll_reset_index")
        )

    try:
        result = PayrollResetService.clear_payroll_history(
            administrator_id=current_user.id,
        )
    except PayrollResetError as error:
        flash(str(error), "danger")
    else:
        _flash_reset_result(
            result=result,
            success_message=(
                "Payroll history was deleted successfully."
            ),
        )

    return redirect(
        url_for("settings.payroll_reset_index")
    )


@settings_bp.route(
    "/payroll-reset/configuration",
    methods=["POST"],
)
@login_required
@admin_required
def reset_payroll_configuration():
    """Delete recurring employee payroll configuration."""

    form = PayrollConfigurationResetForm(
        prefix="configuration"
    )

    if not form.validate_on_submit():
        _flash_form_errors(form)

        return redirect(
            url_for("settings.payroll_reset_index")
        )

    if not _password_is_valid(form):
        flash(
            "The administrator password is incorrect.",
            "danger",
        )

        return redirect(
            url_for("settings.payroll_reset_index")
        )

    try:
        result = (
            PayrollResetService
            .clear_payroll_configuration(
                administrator_id=current_user.id,
            )
        )
    except PayrollResetError as error:
        flash(str(error), "danger")
    else:
        _flash_reset_result(
            result=result,
            success_message=(
                "Recurring payroll configuration was deleted "
                "successfully."
            ),
        )

    return redirect(
        url_for("settings.payroll_reset_index")
    )


@settings_bp.route(
    "/payroll-reset/factory",
    methods=["POST"],
)
@login_required
@admin_required
def reset_payroll_factory():
    """Reset the payroll domain while preserving master data."""

    form = PayrollFactoryResetForm(
        prefix="factory"
    )

    if not form.validate_on_submit():
        _flash_form_errors(form)

        return redirect(
            url_for("settings.payroll_reset_index")
        )

    if not _password_is_valid(form):
        flash(
            "The administrator password is incorrect.",
            "danger",
        )

        return redirect(
            url_for("settings.payroll_reset_index")
        )

    try:
        result = PayrollResetService.factory_reset_payroll(
            administrator_id=current_user.id,
        )
    except PayrollResetError as error:
        flash(str(error), "danger")
    else:
        _flash_reset_result(
            result=result,
            success_message=(
                "The payroll domain was reset successfully."
            ),
        )

    return redirect(
        url_for("settings.payroll_reset_index")
    )
