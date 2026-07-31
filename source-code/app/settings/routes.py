"""Administrator routes for company and payroll settings."""

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from flask import (
    current_app,
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
from werkzeug.utils import secure_filename

from app.auth.permissions import admin_required
from app.extensions import db
from app.models import (
    AllowanceType,
    DeductionType,
    Setting,
)
from app.services.audit_log_service import (
    AuditLogService,
)
from app.settings import settings_bp
from app.settings.forms import (
    AllowanceTypeForm,
    CompanySettingsForm,
    DeductionTypeForm,
)


ZERO = Decimal("0.00")


SETTING_DEFINITIONS = {
    "company_name": {
        "default": "Company",
        "description": "Registered company name.",
    },
    "trading_name": {
        "default": "",
        "description": "Company trading name.",
    },
    "registration_number": {
        "default": "",
        "description": "Company registration number.",
    },
    "tax_number": {
        "default": "",
        "description": "Company tax identification number.",
    },
    "nssa_employer_number": {
        "default": "",
        "description": "NSSA employer registration number.",
    },
    "physical_address": {
        "default": "",
        "description": "Registered physical address.",
    },
    "postal_address": {
        "default": "",
        "description": "Company postal address.",
    },
    "phone": {
        "default": "",
        "description": "Primary company telephone number.",
    },
    "email": {
        "default": "",
        "description": "Primary company email address.",
    },
    "website": {
        "default": "",
        "description": "Company website address.",
    },
    "currency": {
        "default": "USD",
        "description": "Default payroll currency.",
    },
    "payroll_country": {
        "default": "Zimbabwe",
        "description": "Country governing payroll rules.",
    },
    "default_payment_day": {
        "default": "25",
        "description": "Default monthly payroll payment day.",
    },
    "company_logo_path": {
        "default": "",
        "description": "Relative path to the company logo.",
    },
    "payslip_footer": {
        "default": (
            "This payslip is confidential and intended "
            "for the named employee only."
        ),
        "description": "Footer displayed on generated payslips.",
    },
    "payslip_email_subject": {
        "default": (
            "Your Payslip - {period_name}"
        ),
        "description": "Default payslip email subject.",
    },
    "payslip_email_message": {
        "default": (
            "Dear {employee_name},\n\n"
            "Please find attached your payslip for "
            "{period_name}.\n\n"
            "Regards,\n"
            "Payroll Department"
        ),
        "description": "Default payslip email message.",
    },
}


ALLOWED_LOGO_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


COMPANY_UPLOAD_DIRECTORY = Path(
    "static",
    "uploads",
    "company",
)


def _get_setting(setting_key):
    """Return a setting record by key."""

    return Setting.query.filter_by(
        setting_key=setting_key
    ).first()


def _get_setting_value(setting_key):
    """Return a stored value or configured default."""

    definition = SETTING_DEFINITIONS[
        setting_key
    ]

    setting = _get_setting(
        setting_key
    )

    if setting is None:
        return definition["default"]

    return setting.setting_value


def _save_setting(
    setting_key,
    value,
):
    """Create or update one setting record."""

    definition = SETTING_DEFINITIONS[
        setting_key
    ]

    setting = _get_setting(
        setting_key
    )

    normalised_value = (
        str(value).strip()
        if value is not None
        else ""
    )

    if setting is None:
        setting = Setting(
            setting_key=setting_key,
            setting_value=normalised_value,
            description=definition[
                "description"
            ],
            updated_by=current_user.id,
        )

        db.session.add(
            setting
        )

    else:
        setting.setting_value = (
            normalised_value
        )

        setting.description = definition[
            "description"
        ]

        setting.updated_by = (
            current_user.id
        )


def _get_upload_directory():
    """Return and create the company upload directory."""

    upload_directory = (
        Path(current_app.root_path)
        / COMPANY_UPLOAD_DIRECTORY
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return upload_directory


def _delete_company_logo(
    relative_path,
):
    """Delete a company logo safely."""

    if not relative_path:
        return

    relative_path_object = Path(
        relative_path
    )

    expected_prefix = Path(
        "uploads",
        "company",
    )

    try:
        relative_path_object.relative_to(
            expected_prefix
        )

    except ValueError:
        return

    static_directory = Path(
        current_app.static_folder
    ).resolve()

    logo_path = (
        static_directory
        / relative_path_object
    ).resolve()

    try:
        logo_path.relative_to(
            static_directory
        )

    except ValueError:
        return

    if logo_path.is_file():
        logo_path.unlink()


def _save_company_logo(
    uploaded_file,
):
    """Save a company logo and return its relative path."""

    original_filename = secure_filename(
        uploaded_file.filename or ""
    )

    extension = Path(
        original_filename
    ).suffix.lower()

    if extension not in ALLOWED_LOGO_EXTENSIONS:
        raise ValueError(
            "Unsupported company logo file type."
        )

    unique_filename = (
        f"company-logo-{uuid4().hex}"
        f"{extension}"
    )

    upload_directory = (
        _get_upload_directory()
    )

    destination = (
        upload_directory
        / unique_filename
    )

    uploaded_file.save(
        destination
    )

    return (
        Path(
            "uploads",
            "company",
            unique_filename,
        )
        .as_posix()
    )


def _get_latest_update():
    """Return the most recent company-setting update."""

    return (
        Setting.query
        .filter(
            Setting.setting_key.in_(
                SETTING_DEFINITIONS.keys()
            )
        )
        .order_by(
            Setting.updated_at.desc()
        )
        .first()
    )


def _populate_company_form(
    form,
):
    """Populate the company settings form."""

    form.company_name.data = (
        _get_setting_value(
            "company_name"
        )
    )

    form.trading_name.data = (
        _get_setting_value(
            "trading_name"
        )
    )

    form.registration_number.data = (
        _get_setting_value(
            "registration_number"
        )
    )

    form.tax_number.data = (
        _get_setting_value(
            "tax_number"
        )
    )

    form.nssa_employer_number.data = (
        _get_setting_value(
            "nssa_employer_number"
        )
    )

    form.physical_address.data = (
        _get_setting_value(
            "physical_address"
        )
    )

    form.postal_address.data = (
        _get_setting_value(
            "postal_address"
        )
    )

    form.phone.data = (
        _get_setting_value(
            "phone"
        )
    )

    form.email.data = (
        _get_setting_value(
            "email"
        )
    )

    form.website.data = (
        _get_setting_value(
            "website"
        )
    )

    form.currency.data = (
        _get_setting_value(
            "currency"
        )
    )

    form.payroll_country.data = (
        _get_setting_value(
            "payroll_country"
        )
    )

    payment_day = _get_setting_value(
        "default_payment_day"
    )

    try:
        form.default_payment_day.data = int(
            payment_day
        )

    except (
        TypeError,
        ValueError,
    ):
        form.default_payment_day.data = 25

    form.payslip_footer.data = (
        _get_setting_value(
            "payslip_footer"
        )
    )

    form.payslip_email_subject.data = (
        _get_setting_value(
            "payslip_email_subject"
        )
    )

    form.payslip_email_message.data = (
        _get_setting_value(
            "payslip_email_message"
        )
    )


def _normalise_code(
    value,
):
    """Normalise a payroll configuration code."""

    code = str(
        value or ""
    ).strip().upper()

    code = code.replace(
        "-",
        "_",
    )

    code = code.replace(
        " ",
        "_",
    )

    while "__" in code:
        code = code.replace(
            "__",
            "_",
        )

    return code


def _decimal_or_zero(
    value,
):
    """Return a Decimal or zero."""

    if value is None:
        return ZERO

    return Decimal(
        str(value)
    )


def _populate_allowance_form(
    form,
    allowance_type,
):
    """Populate the allowance edit form."""

    form.allowance_type_id.data = str(
        allowance_type.id
    )

    form.name.data = (
        allowance_type.name
    )

    form.code.data = (
        allowance_type.code
    )

    form.description.data = (
        allowance_type.description
    )

    form.calculation_method.data = (
        allowance_type.calculation_method
    )

    form.default_amount.data = (
        allowance_type.default_amount
    )

    form.default_percentage.data = (
        allowance_type.default_percentage
    )

    form.is_taxable.data = (
        allowance_type.is_taxable
    )

    form.is_recurring.data = (
        allowance_type.is_recurring
    )

    form.is_active.data = (
        allowance_type.is_active
    )


def _populate_deduction_form(
    form,
    deduction_type,
):
    """Populate the deduction edit form."""

    form.deduction_type_id.data = str(
        deduction_type.id
    )

    form.name.data = (
        deduction_type.name
    )

    form.code.data = (
        deduction_type.code
    )

    form.description.data = (
        deduction_type.description
    )

    form.category.data = (
        deduction_type.category
    )

    form.calculation_method.data = (
        deduction_type.calculation_method
    )

    form.default_amount.data = (
        deduction_type.default_amount
    )

    form.default_percentage.data = (
        deduction_type.default_percentage
    )

    form.employer_percentage.data = (
        deduction_type.employer_percentage
    )

    form.is_statutory.data = (
        deduction_type.is_statutory
    )

    form.reduces_net_pay.data = (
        deduction_type.reduces_net_pay
    )

    form.is_recurring.data = (
        deduction_type.is_recurring
    )

    form.is_active.data = (
        deduction_type.is_active
    )


@settings_bp.route(
    "/",
    methods=[
        "GET",
        "POST",
    ],
)
@login_required
@admin_required
def index():
    """Display and update settings."""

    company_form = CompanySettingsForm(
        prefix="company"
    )

    allowance_form = AllowanceTypeForm(
        prefix="allowance"
    )

    deduction_form = DeductionTypeForm(
        prefix="deduction"
    )

    current_logo_path = (
        _get_setting_value(
            "company_logo_path"
        )
    )

    if (
        request.method == "POST"
        and company_form.validate_on_submit()
    ):
        new_logo_path = (
            current_logo_path
        )

        try:
            if (
                company_form
                .remove_company_logo
                .data
            ):
                _delete_company_logo(
                    current_logo_path
                )

                new_logo_path = ""

            if (
                company_form.company_logo.data
                and company_form
                .company_logo
                .data
                .filename
            ):
                uploaded_logo_path = (
                    _save_company_logo(
                        company_form
                        .company_logo
                        .data
                    )
                )

                if current_logo_path:
                    _delete_company_logo(
                        current_logo_path
                    )

                new_logo_path = (
                    uploaded_logo_path
                )

            company_fields = {
                "company_name": (
                    company_form
                    .company_name
                    .data
                ),
                "trading_name": (
                    company_form
                    .trading_name
                    .data
                ),
                "registration_number": (
                    company_form
                    .registration_number
                    .data
                ),
                "tax_number": (
                    company_form
                    .tax_number
                    .data
                ),
                "nssa_employer_number": (
                    company_form
                    .nssa_employer_number
                    .data
                ),
                "physical_address": (
                    company_form
                    .physical_address
                    .data
                ),
                "postal_address": (
                    company_form
                    .postal_address
                    .data
                ),
                "phone": (
                    company_form.phone.data
                ),
                "email": (
                    company_form.email.data
                ),
                "website": (
                    company_form.website.data
                ),
                "currency": (
                    company_form.currency.data
                ),
                "payroll_country": (
                    company_form
                    .payroll_country
                    .data
                ),
                "default_payment_day": (
                    company_form
                    .default_payment_day
                    .data
                ),
                "company_logo_path": (
                    new_logo_path
                ),
                "payslip_footer": (
                    company_form
                    .payslip_footer
                    .data
                ),
                "payslip_email_subject": (
                    company_form
                    .payslip_email_subject
                    .data
                ),
                "payslip_email_message": (
                    company_form
                    .payslip_email_message
                    .data
                ),
            }

            for (
                setting_key,
                setting_value,
            ) in company_fields.items():
                _save_setting(
                    setting_key,
                    setting_value,
                )

            AuditLogService.log(
                user_id=current_user.id,
                action="Company Settings Updated",
                entity_type="Setting",
                description=(
                    "Updated company identity and "
                    "payroll defaults."
                ),
                commit=False,
            )

            db.session.commit()

        except (
            OSError,
            ValueError,
        ) as error:
            db.session.rollback()

            flash(
                (
                    "The company settings could not "
                    f"be saved: {error}"
                ),
                "danger",
            )

        else:
            flash(
                "Company settings saved successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "settings.index",
                    tab="company",
                )
            )

    elif request.method == "GET":
        _populate_company_form(
            company_form
        )

    edit_allowance_id = request.args.get(
        "edit_allowance",
        type=int,
    )

    if edit_allowance_id:
        allowance_type = (
            db.session.get(
                AllowanceType,
                edit_allowance_id,
            )
        )

        if allowance_type:
            _populate_allowance_form(
                allowance_form,
                allowance_type,
            )

    edit_deduction_id = request.args.get(
        "edit_deduction",
        type=int,
    )

    if edit_deduction_id:
        deduction_type = (
            db.session.get(
                DeductionType,
                edit_deduction_id,
            )
        )

        if deduction_type:
            _populate_deduction_form(
                deduction_form,
                deduction_type,
            )

    allowance_types = (
        AllowanceType.query
        .order_by(
            AllowanceType.is_active.desc(),
            AllowanceType.name.asc(),
        )
        .all()
    )

    deduction_types = (
        DeductionType.query
        .order_by(
            DeductionType.is_active.desc(),
            DeductionType.name.asc(),
        )
        .all()
    )

    latest_update = (
        _get_latest_update()
    )

    current_logo_path = (
        _get_setting_value(
            "company_logo_path"
        )
    )

    current_logo_url = None

    if current_logo_path:
        current_logo_url = url_for(
            "static",
            filename=current_logo_path,
        )

    active_tab = request.args.get(
        "tab",
        "company",
    )

    return render_template(
        "settings/index.html",
        company_form=company_form,
        allowance_form=allowance_form,
        deduction_form=deduction_form,
        allowance_types=allowance_types,
        deduction_types=deduction_types,
        latest_update=latest_update,
        current_logo_path=current_logo_path,
        current_logo_url=current_logo_url,
        active_tab=active_tab,
    )


@settings_bp.route(
    "/allowance-types/save",
    methods=["POST"],
)
@login_required
@admin_required
def save_allowance_type():
    """Create or update an allowance type."""

    form = AllowanceTypeForm(
        prefix="allowance"
    )

    if not form.validate_on_submit():
        flash(
            (
                "Allowance type could not be saved. "
                "Please review the form fields."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "settings.index",
                tab="allowances",
            )
        )

    allowance_type = None

    if form.allowance_type_id.data:
        try:
            allowance_type_id = int(
                form.allowance_type_id.data
            )

        except ValueError:
            allowance_type_id = None

        if allowance_type_id:
            allowance_type = (
                db.session.get(
                    AllowanceType,
                    allowance_type_id,
                )
            )

    is_new = allowance_type is None

    if is_new:
        allowance_type = AllowanceType(
            created_by=current_user.id,
        )

        db.session.add(
            allowance_type
        )

    allowance_type.name = (
        form.name.data.strip()
    )

    allowance_type.code = (
        _normalise_code(
            form.code.data
        )
    )

    allowance_type.description = (
        form.description.data.strip()
        if form.description.data
        else None
    )

    allowance_type.calculation_method = (
        form.calculation_method.data
    )

    allowance_type.default_amount = (
        _decimal_or_zero(
            form.default_amount.data
        )
    )

    allowance_type.default_percentage = (
        _decimal_or_zero(
            form.default_percentage.data
        )
    )

    allowance_type.is_taxable = (
        bool(
            form.is_taxable.data
        )
    )

    allowance_type.is_recurring = (
        bool(
            form.is_recurring.data
        )
    )

    allowance_type.is_active = (
        bool(
            form.is_active.data
        )
    )

    try:
        AuditLogService.log(
            user_id=current_user.id,
            action=(
                "Allowance Type Created"
                if is_new
                else "Allowance Type Updated"
            ),
            entity_type="AllowanceType",
            entity_id=allowance_type.id,
            description=(
                f"{'Created' if is_new else 'Updated'} "
                f"allowance type "
                f"{allowance_type.name}."
            ),
            commit=False,
        )

        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        flash(
            (
                "An allowance type with that name "
                "or code already exists."
            ),
            "danger",
        )

    else:
        flash(
            (
                "Allowance type created successfully."
                if is_new
                else (
                    "Allowance type updated "
                    "successfully."
                )
            ),
            "success",
        )

    return redirect(
        url_for(
            "settings.index",
            tab="allowances",
        )
    )


@settings_bp.route(
    "/allowance-types/<int:allowance_type_id>/toggle",
    methods=["POST"],
)
@login_required
@admin_required
def toggle_allowance_type(
    allowance_type_id,
):
    """Activate or deactivate an allowance type."""

    allowance_type = (
        AllowanceType.query.get_or_404(
            allowance_type_id
        )
    )

    allowance_type.is_active = (
        not allowance_type.is_active
    )

    AuditLogService.log(
        user_id=current_user.id,
        action="Allowance Type Status Changed",
        entity_type="AllowanceType",
        entity_id=allowance_type.id,
        description=(
            f"{allowance_type.name} was "
            f"{'activated' if allowance_type.is_active else 'deactivated'}."
        ),
        commit=False,
    )

    db.session.commit()

    flash(
        (
            f"{allowance_type.name} "
            f"{'activated' if allowance_type.is_active else 'deactivated'} "
            "successfully."
        ),
        "success",
    )

    return redirect(
        url_for(
            "settings.index",
            tab="allowances",
        )
    )


@settings_bp.route(
    "/deduction-types/save",
    methods=["POST"],
)
@login_required
@admin_required
def save_deduction_type():
    """Create or update a deduction type."""

    form = DeductionTypeForm(
        prefix="deduction"
    )

    if not form.validate_on_submit():
        flash(
            (
                "Deduction type could not be saved. "
                "Please review the form fields."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "settings.index",
                tab="deductions",
            )
        )

    deduction_type = None

    if form.deduction_type_id.data:
        try:
            deduction_type_id = int(
                form.deduction_type_id.data
            )

        except ValueError:
            deduction_type_id = None

        if deduction_type_id:
            deduction_type = (
                db.session.get(
                    DeductionType,
                    deduction_type_id,
                )
            )

    is_new = deduction_type is None

    if is_new:
        deduction_type = DeductionType(
            created_by=current_user.id,
        )

        db.session.add(
            deduction_type
        )

    deduction_type.name = (
        form.name.data.strip()
    )

    deduction_type.code = (
        _normalise_code(
            form.code.data
        )
    )

    deduction_type.description = (
        form.description.data.strip()
        if form.description.data
        else None
    )

    deduction_type.category = (
        form.category.data
    )

    deduction_type.calculation_method = (
        form.calculation_method.data
    )

    deduction_type.default_amount = (
        _decimal_or_zero(
            form.default_amount.data
        )
    )

    deduction_type.default_percentage = (
        _decimal_or_zero(
            form.default_percentage.data
        )
    )

    deduction_type.employer_percentage = (
        _decimal_or_zero(
            form.employer_percentage.data
        )
    )

    deduction_type.is_statutory = (
        bool(
            form.is_statutory.data
        )
    )

    deduction_type.reduces_net_pay = (
        bool(
            form.reduces_net_pay.data
        )
    )

    deduction_type.is_recurring = (
        bool(
            form.is_recurring.data
        )
    )

    deduction_type.is_active = (
        bool(
            form.is_active.data
        )
    )

    try:
        AuditLogService.log(
            user_id=current_user.id,
            action=(
                "Deduction Type Created"
                if is_new
                else "Deduction Type Updated"
            ),
            entity_type="DeductionType",
            entity_id=deduction_type.id,
            description=(
                f"{'Created' if is_new else 'Updated'} "
                f"deduction type "
                f"{deduction_type.name}."
            ),
            commit=False,
        )

        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        flash(
            (
                "A deduction type with that name "
                "or code already exists."
            ),
            "danger",
        )

    else:
        flash(
            (
                "Deduction type created successfully."
                if is_new
                else (
                    "Deduction type updated "
                    "successfully."
                )
            ),
            "success",
        )

    return redirect(
        url_for(
            "settings.index",
            tab="deductions",
        )
    )


@settings_bp.route(
    "/deduction-types/<int:deduction_type_id>/toggle",
    methods=["POST"],
)
@login_required
@admin_required
def toggle_deduction_type(
    deduction_type_id,
):
    """Activate or deactivate a deduction type."""

    deduction_type = (
        DeductionType.query.get_or_404(
            deduction_type_id
        )
    )

    deduction_type.is_active = (
        not deduction_type.is_active
    )

    AuditLogService.log(
        user_id=current_user.id,
        action="Deduction Type Status Changed",
        entity_type="DeductionType",
        entity_id=deduction_type.id,
        description=(
            f"{deduction_type.name} was "
            f"{'activated' if deduction_type.is_active else 'deactivated'}."
        ),
        commit=False,
    )

    db.session.commit()

    flash(
        (
            f"{deduction_type.name} "
            f"{'activated' if deduction_type.is_active else 'deactivated'} "
            "successfully."
        ),
        "success",
    )

    return redirect(
        url_for(
            "settings.index",
            tab="deductions",
        )
    )

