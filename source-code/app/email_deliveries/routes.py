"""Routes for the Email Delivery Centre."""

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app.email_deliveries import email_deliveries_bp
from app.email_deliveries.forms import ResendEmailForm
from app.extensions import db
from app.models import (
    EmailDelivery,
    Employee,
    PayrollPeriod,
    User,
)
from app.services.email_service import (
    EmailConfigurationError,
    EmailDeliveryError,
    EmailService,
    InvalidEmployeeEmailError,
    MissingEmployeeEmailError,
    PayslipFileNotFoundError,
)


@email_deliveries_bp.route("/")
@login_required
def index():
    """Display searchable and paginated email history."""

    search = request.args.get(
        "search",
        "",
    ).strip()

    status = request.args.get(
        "status",
        "",
    ).strip()

    period_id = request.args.get(
        "period_id",
        type=int,
    )

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    per_page = 20

    filters = []

    if search:
        search_pattern = f"%{search}%"

        employee_full_name = func.concat(
            Employee.first_name,
            " ",
            Employee.last_name,
        )

        filters.append(
            or_(
                EmailDelivery.recipient_email.ilike(
                    search_pattern
                ),
                Employee.employee_number.ilike(
                    search_pattern
                ),
                Employee.first_name.ilike(
                    search_pattern
                ),
                Employee.last_name.ilike(
                    search_pattern
                ),
                employee_full_name.ilike(
                    search_pattern
                ),
                User.username.ilike(
                    search_pattern
                ),
                User.email.ilike(
                    search_pattern
                ),
            )
        )

    if status in EmailDelivery.VALID_STATUSES:
        filters.append(
            EmailDelivery.status == status
        )

    if period_id:
        filters.append(
            EmailDelivery.payroll_period_id == period_id
        )

    query = (
        EmailDelivery.query
        .join(
            Employee,
            EmailDelivery.employee_id == Employee.id,
        )
        .join(
            PayrollPeriod,
            EmailDelivery.payroll_period_id
            == PayrollPeriod.id,
        )
        .join(
            User,
            EmailDelivery.sent_by_id == User.id,
        )
        .filter(*filters)
        .order_by(
            EmailDelivery.created_at.desc(),
            EmailDelivery.id.desc(),
        )
    )

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    summary_query = EmailDelivery.query.filter(
        *filters
    )

    total_count = summary_query.count()

    delivered_count = summary_query.filter(
        EmailDelivery.status
        == EmailDelivery.STATUS_DELIVERED
    ).count()

    failed_count = summary_query.filter(
        EmailDelivery.status
        == EmailDelivery.STATUS_FAILED
    ).count()

    pending_count = summary_query.filter(
        EmailDelivery.status
        == EmailDelivery.STATUS_PENDING
    ).count()

    periods = (
        PayrollPeriod.query
        .order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc(),
        )
        .all()
    )

    resend_form = ResendEmailForm()

    return render_template(
        "email_deliveries/index.html",
        deliveries=pagination.items,
        pagination=pagination,
        periods=periods,
        resend_form=resend_form,
        search=search,
        selected_status=status,
        selected_period_id=period_id,
        total_count=total_count,
        delivered_count=delivered_count,
        failed_count=failed_count,
        pending_count=pending_count,
    )


@email_deliveries_bp.route(
    "/<int:delivery_id>/resend",
    methods=["POST"],
)
@login_required
def resend(delivery_id):
    """Resend the payslip from an existing delivery record."""

    original_delivery = EmailDelivery.query.get_or_404(
        delivery_id
    )

    form = ResendEmailForm()

    if not form.validate_on_submit():
        flash(
            "The resend request could not be validated.",
            "danger",
        )

        return redirect(
            url_for("email_deliveries.index")
        )

    try:
        new_delivery = EmailService.send_payslip(
            payslip=original_delivery.payslip,
            sent_by_user_id=current_user.id,
            ip_address=request.remote_addr,
        )

    except (
        MissingEmployeeEmailError,
        InvalidEmployeeEmailError,
        PayslipFileNotFoundError,
        EmailConfigurationError,
        EmailDeliveryError,
    ) as error:
        flash(
            f"The payslip email could not be resent: {error}",
            "danger",
        )

    else:
        flash(
            "The payslip was resent successfully to "
            f"{new_delivery.recipient_email}.",
            "success",
        )

    return redirect(
        url_for("email_deliveries.index")
    )
