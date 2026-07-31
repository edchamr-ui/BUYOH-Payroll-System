"""Email delivery services for employee payslips."""

import mimetypes
import smtplib
from email.message import EmailMessage
from html import escape
from pathlib import Path

from email_validator import (
    EmailNotValidError,
    validate_email,
)
from flask import current_app

from app.extensions import db
from app.models.email_delivery import EmailDelivery
from app.services.audit_log_service import AuditLogService
from app.services.company_settings_service import (
    CompanySettingsService,
)


class EmailServiceError(Exception):
    """Base exception for email service failures."""


class MissingEmployeeEmailError(EmailServiceError):
    """Raised when an employee has no email address."""


class InvalidEmployeeEmailError(EmailServiceError):
    """Raised when an employee email address is invalid."""


class PayslipFileNotFoundError(EmailServiceError):
    """Raised when the generated payslip PDF cannot be found."""


class EmailConfigurationError(EmailServiceError):
    """Raised when SMTP configuration is incomplete."""


class EmailDeliveryError(EmailServiceError):
    """Raised when an email cannot be delivered."""


class EmailService:
    """Send generated payslip PDFs and persist delivery history."""

    @staticmethod
    def _get_required_config(config_name):
        """Return a required Flask configuration value."""

        value = current_app.config.get(config_name)

        if value is None:
            raise EmailConfigurationError(
                f"{config_name} has not been configured."
            )

        if isinstance(value, str) and not value.strip():
            raise EmailConfigurationError(
                f"{config_name} has not been configured."
            )

        return value

    @classmethod
    def _load_smtp_config(cls):
        """Load and validate SMTP settings."""

        mail_server = cls._get_required_config(
            "MAIL_SERVER"
        )

        mail_port = cls._get_required_config(
            "MAIL_PORT"
        )

        mail_username = cls._get_required_config(
            "MAIL_USERNAME"
        )

        mail_password = cls._get_required_config(
            "MAIL_PASSWORD"
        )

        default_sender = cls._get_required_config(
            "MAIL_DEFAULT_SENDER"
        )

        use_tls = current_app.config.get(
            "MAIL_USE_TLS",
            True,
        )

        use_ssl = current_app.config.get(
            "MAIL_USE_SSL",
            False,
        )

        try:
            mail_port = int(mail_port)

        except (TypeError, ValueError) as error:
            raise EmailConfigurationError(
                "MAIL_PORT must be a valid integer."
            ) from error

        if use_tls and use_ssl:
            raise EmailConfigurationError(
                "MAIL_USE_TLS and MAIL_USE_SSL cannot "
                "both be enabled."
            )

        return {
            "server": str(mail_server).strip(),
            "port": mail_port,
            "username": str(mail_username).strip(),
            "password": str(mail_password),
            "sender": str(default_sender).strip(),
            "use_tls": bool(use_tls),
            "use_ssl": bool(use_ssl),
        }

    @staticmethod
    def _raw_recipient_email(employee):
        """Return the employee's raw email value."""

        email_address = getattr(
            employee,
            "email",
            "",
        )

        return str(
            email_address or ""
        ).strip()

    @staticmethod
    def _validate_recipient_email(employee):
        """Return a normalised employee email address."""

        email_address = EmailService._raw_recipient_email(
            employee
        )

        if not email_address:
            raise MissingEmployeeEmailError(
                "This employee does not have an email address."
            )

        try:
            validation_result = validate_email(
                email_address,
                check_deliverability=False,
            )

        except EmailNotValidError as error:
            raise InvalidEmployeeEmailError(
                "The employee email address is invalid."
            ) from error

        return validation_result.normalized

    @staticmethod
    def _validate_payslip_file(payslip):
        """Return a verified generated payslip PDF path."""

        file_path_value = getattr(
            payslip,
            "file_path",
            None,
        )

        if not file_path_value:
            raise PayslipFileNotFoundError(
                "The payslip does not have a PDF file path."
            )

        file_path = Path(
            file_path_value
        ).resolve()

        if not file_path.exists() or not file_path.is_file():
            raise PayslipFileNotFoundError(
                "The generated payslip PDF could not be "
                "found. Please regenerate the payslip."
            )

        if file_path.suffix.lower() != ".pdf":
            raise PayslipFileNotFoundError(
                "The stored payslip file is not a PDF."
            )

        return file_path

    @staticmethod
    def _employee_name(employee):
        """Return the employee's full display name."""

        full_name = getattr(
            employee,
            "full_name",
            None,
        )

        if full_name:
            return str(full_name).strip()

        first_name = getattr(
            employee,
            "first_name",
            "",
        )

        last_name = getattr(
            employee,
            "last_name",
            "",
        )

        combined_name = (
            f"{first_name} {last_name}"
        ).strip()

        return combined_name or "Employee"

    @staticmethod
    def _period_name(payslip):
        """Return the payroll period display name."""

        payroll_record = getattr(
            payslip,
            "payroll_record",
            None,
        )

        if payroll_record is None:
            return "Payroll Period"

        payroll_period = getattr(
            payroll_record,
            "payroll_period",
            None,
        )

        if payroll_period is None:
            return "Payroll Period"

        period_name = getattr(
            payroll_period,
            "period_name",
            None,
        )

        return (
            str(period_name).strip()
            if period_name
            else "Payroll Period"
        )

    @staticmethod
    def _payroll_period_id(payslip):
        """Return the payslip payroll-period ID."""

        payroll_record = getattr(
            payslip,
            "payroll_record",
            None,
        )

        if payroll_record is None:
            raise EmailDeliveryError(
                "The payslip is not connected to a payroll record."
            )

        payroll_period_id = getattr(
            payroll_record,
            "payroll_period_id",
            None,
        )

        if payroll_period_id is None:
            raise EmailDeliveryError(
                "The payslip is not connected to a payroll period."
            )

        return payroll_period_id

    @staticmethod
    def _company_profile():
        """Return the configured company profile."""

        return (
            CompanySettingsService.get_company_profile()
        )

    @staticmethod
    def _company_display_name(company_profile):
        """Return the configured company display name."""

        return str(
            company_profile.get(
                "display_name",
                "",
            )
            or company_profile.get(
                "company_name",
                "",
            )
            or "Company"
        ).strip()

    @staticmethod
    def _company_contact_line(company_profile):
        """Return a compact contact line for the email footer."""

        contact_parts = []

        company_email = str(
            company_profile.get(
                "email",
                "",
            )
            or ""
        ).strip()

        phone = str(
            company_profile.get(
                "phone",
                "",
            )
            or ""
        ).strip()

        website = str(
            company_profile.get(
                "website",
                "",
            )
            or ""
        ).strip()

        if company_email:
            contact_parts.append(
                company_email
            )

        if phone:
            contact_parts.append(
                phone
            )

        if website:
            contact_parts.append(
                website
            )

        return " | ".join(
            contact_parts
        )

    @classmethod
    def _create_delivery_attempt(
        cls,
        *,
        payslip,
        sent_by_user_id,
    ):
        """Create and commit a pending delivery record."""

        employee = payslip.employee

        raw_email = cls._raw_recipient_email(
            employee
        )

        delivery = EmailDelivery.create_pending(
            employee_id=employee.id,
            payslip_id=payslip.id,
            payroll_period_id=cls._payroll_period_id(
                payslip
            ),
            recipient_email=raw_email,
            sent_by_id=sent_by_user_id,
        )

        try:
            db.session.add(delivery)
            db.session.commit()

        except Exception as error:
            db.session.rollback()

            current_app.logger.exception(
                "Could not create the email delivery record."
            )

            raise EmailDeliveryError(
                "The email attempt could not be recorded."
            ) from error

        return delivery

    @staticmethod
    def _save_delivery_result(delivery):
        """Commit a completed delivery result."""

        try:
            db.session.add(delivery)
            db.session.commit()

        except Exception as error:
            db.session.rollback()

            current_app.logger.exception(
                "Could not update the email delivery record."
            )

            raise EmailDeliveryError(
                "The email delivery result could not be saved."
            ) from error

    @classmethod
    def _mark_delivery_failed(
        cls,
        *,
        delivery,
        error,
    ):
        """Persist a failed delivery result."""

        delivery.mark_failed(
            str(error)
        )

        try:
            cls._save_delivery_result(
                delivery
            )

        except EmailDeliveryError:
            current_app.logger.exception(
                "The failed email result could not be persisted."
            )

    @classmethod
    def _build_message(
        cls,
        *,
        payslip,
        recipient_email,
        sender_email,
    ):
        """Create the settings-driven payslip email."""

        employee = payslip.employee

        employee_name = cls._employee_name(
            employee
        )

        period_name = cls._period_name(
            payslip
        )

        file_path = cls._validate_payslip_file(
            payslip
        )

        company_profile = cls._company_profile()

        company_name = cls._company_display_name(
            company_profile
        )

        company_logo_url = str(
            company_profile.get(
                "company_logo_url",
                "",
            )
            or ""
        ).strip()

        company_contact_line = cls._company_contact_line(
            company_profile
        )

        subject = (
            CompanySettingsService.format_email_subject(
                employee_name=employee_name,
                period_name=period_name,
            )
        )

        plain_text_body = (
            CompanySettingsService.format_email_message(
                employee_name=employee_name,
                period_name=period_name,
            )
        )

        if not subject.strip():
            subject = (
                f"Payslip for {period_name}"
            )

        if not plain_text_body.strip():
            plain_text_body = (
                f"Dear {employee_name},\n\n"
                f"Please find attached your payslip for "
                f"{period_name}.\n\n"
                f"Regards,\n"
                f"{company_name}"
            )

        message = EmailMessage()

        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = recipient_email

        message.set_content(
            plain_text_body
        )

        escaped_employee_name = escape(
            employee_name
        )

        escaped_period_name = escape(
            period_name
        )

        escaped_company_name = escape(
            company_name
        )

        escaped_contact_line = escape(
            company_contact_line
        )

        html_message_body = cls._plain_text_to_html(
            plain_text_body
        )

        logo_html = ""

        if company_logo_url:
            logo_html = f"""
                <img
                    src="{escape(company_logo_url)}"
                    alt="{escaped_company_name} logo"
                    style="
                        display: block;
                        max-width: 150px;
                        max-height: 70px;
                        object-fit: contain;
                        margin-bottom: 14px;
                    "
                >
            """

        contact_html = ""

        if company_contact_line:
            contact_html = f"""
                <div
                    style="
                        margin-top: 8px;
                        color: #6c757d;
                        font-size: 12px;
                    "
                >
                    {escaped_contact_line}
                </div>
            """

        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >
        </head>

        <body
            style="
                margin: 0;
                padding: 24px;
                background-color: #f4f6f8;
                font-family: Arial, Helvetica, sans-serif;
                color: #212529;
            "
        >
            <div
                style="
                    max-width: 620px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border: 1px solid #dee2e6;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 8px 24px rgba(33, 37, 41, 0.08);
                "
            >
                <div
                    style="
                        background-color: #163A72;
                        color: #ffffff;
                        padding: 22px 26px;
                    "
                >
                    {logo_html}

                    <h1
                        style="
                            margin: 0;
                            font-size: 22px;
                            line-height: 1.3;
                        "
                    >
                        {escaped_company_name}
                    </h1>

                    <div
                        style="
                            margin-top: 4px;
                            font-size: 13px;
                            opacity: 0.9;
                        "
                    >
                        Payroll Management System
                    </div>
                </div>

                <div style="padding: 26px;">
                    <div
                        style="
                            font-size: 15px;
                            line-height: 1.7;
                        "
                    >
                        {html_message_body}
                    </div>

                    <div
                        style="
                            margin-top: 26px;
                            padding: 14px 16px;
                            background-color: #f8f9fa;
                            border-left: 4px solid #163A72;
                            border-radius: 4px;
                            font-size: 13px;
                            color: #495057;
                        "
                    >
                        Attached document:
                        <strong>
                            Payslip for {escaped_period_name}
                        </strong>
                    </div>

                    <div
                        style="
                            margin-top: 20px;
                            font-size: 12px;
                            color: #6c757d;
                        "
                    >
                        This document contains confidential payroll
                        information. Please store it securely.
                    </div>
                </div>

                <div
                    style="
                        padding: 16px 26px;
                        background-color: #f8f9fa;
                        border-top: 1px solid #e9ecef;
                        color: #6c757d;
                        font-size: 12px;
                    "
                >
                    <strong>
                        {escaped_company_name}
                    </strong>

                    {contact_html}

                    <div style="margin-top: 10px;">
                        This email was generated automatically by the
                        payroll system.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        message.add_alternative(
            html_body,
            subtype="html",
        )

        mime_type, _ = mimetypes.guess_type(
            str(file_path)
        )

        if mime_type:
            main_type, sub_type = mime_type.split(
                "/",
                1,
            )

        else:
            main_type = "application"
            sub_type = "pdf"

        with file_path.open("rb") as pdf_file:
            message.add_attachment(
                pdf_file.read(),
                maintype=main_type,
                subtype=sub_type,
                filename=file_path.name,
            )

        return message

    @staticmethod
    def _plain_text_to_html(text):
        """Convert plain text into safe email HTML."""

        escaped_text = escape(
            str(text or "")
        )

        paragraphs = escaped_text.split(
            "\n\n"
        )

        html_paragraphs = []

        for paragraph in paragraphs:
            paragraph = paragraph.replace(
                "\n",
                "<br>",
            )

            if paragraph.strip():
                html_paragraphs.append(
                    f'<p style="margin: 0 0 16px;">'
                    f"{paragraph}"
                    f"</p>"
                )

        return "".join(
            html_paragraphs
        )

    @staticmethod
    def _send_message(
        *,
        message,
        smtp_config,
    ):
        """Send a prepared email through SMTP."""

        smtp_connection = None

        try:
            if smtp_config["use_ssl"]:
                smtp_connection = smtplib.SMTP_SSL(
                    smtp_config["server"],
                    smtp_config["port"],
                    timeout=30,
                )

            else:
                smtp_connection = smtplib.SMTP(
                    smtp_config["server"],
                    smtp_config["port"],
                    timeout=30,
                )

                smtp_connection.ehlo()

                if smtp_config["use_tls"]:
                    smtp_connection.starttls()
                    smtp_connection.ehlo()

            smtp_connection.login(
                smtp_config["username"],
                smtp_config["password"],
            )

            smtp_connection.send_message(
                message
            )

        except (
            smtplib.SMTPException,
            OSError,
            TimeoutError,
        ) as error:
            raise EmailDeliveryError(
                "The payslip email could not be sent. "
                "Please check the SMTP configuration and "
                "internet connection."
            ) from error

        finally:
            if smtp_connection is not None:
                try:
                    smtp_connection.quit()

                except (
                    smtplib.SMTPException,
                    OSError,
                ):
                    pass

    @classmethod
    def send_payslip(
        cls,
        *,
        payslip,
        sent_by_user_id,
        ip_address=None,
    ):
        """
        Email one generated payslip to its employee.

        A new EmailDelivery record is created for every call.
        Returns the completed EmailDelivery record.
        """

        employee = payslip.employee

        delivery = cls._create_delivery_attempt(
            payslip=payslip,
            sent_by_user_id=sent_by_user_id,
        )

        employee_name = cls._employee_name(
            employee
        )

        period_name = cls._period_name(
            payslip
        )

        try:
            recipient_email = cls._validate_recipient_email(
                employee
            )

            delivery.recipient_email = (
                recipient_email
            )

            smtp_config = cls._load_smtp_config()

            message = cls._build_message(
                payslip=payslip,
                recipient_email=recipient_email,
                sender_email=smtp_config["sender"],
            )

            cls._send_message(
                message=message,
                smtp_config=smtp_config,
            )

        except EmailServiceError as error:
            cls._mark_delivery_failed(
                delivery=delivery,
                error=error,
            )

            cls._log_failure(
                payslip=payslip,
                user_id=sent_by_user_id,
                ip_address=ip_address,
                recipient_email=(
                    delivery.recipient_email
                    or "No email address"
                ),
                employee_name=employee_name,
                period_name=period_name,
                error_message=str(error),
            )

            raise

        delivery.mark_delivered()

        cls._save_delivery_result(
            delivery
        )

        try:
            AuditLogService.log(
                action="PAYSLIP_EMAIL_SENT",
                user_id=sent_by_user_id,
                entity_type="Payslip",
                entity_id=payslip.id,
                description=(
                    f"Payslip for {employee_name} "
                    f"for {period_name} was emailed to "
                    f"{recipient_email}."
                ),
                ip_address=ip_address,
            )

        except Exception:
            current_app.logger.exception(
                "The successful payslip email could not be "
                "written to the audit log."
            )

        return delivery

    @staticmethod
    def _log_failure(
        *,
        payslip,
        user_id,
        ip_address,
        recipient_email,
        employee_name,
        period_name,
        error_message,
    ):
        """Record a failed payslip email attempt."""

        try:
            AuditLogService.log(
                action="PAYSLIP_EMAIL_FAILED",
                user_id=user_id,
                entity_type="Payslip",
                entity_id=payslip.id,
                description=(
                    f"Failed to email the payslip for "
                    f"{employee_name} for {period_name} "
                    f"to {recipient_email}. "
                    f"Reason: {error_message}"
                ),
                ip_address=ip_address,
            )

        except Exception:
            current_app.logger.exception(
                "The failed payslip email attempt could "
                "not be written to the audit log."
            )
