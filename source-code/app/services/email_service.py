"""Email delivery services for employee payslips."""

import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path

from email_validator import (
    EmailNotValidError,
    validate_email,
)
from flask import current_app

from app.services.audit_log_service import AuditLogService


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
    """Raised when the SMTP server cannot deliver an email."""


class EmailService:
    """Send generated payslip PDFs to employees through SMTP."""

    @staticmethod
    def _get_required_config(config_name):
        """Return a required Flask configuration value."""

        value = current_app.config.get(config_name)

        if value is None:
            raise EmailConfigurationError(
                f"{config_name} has not been configured."
            )

        if (
            isinstance(value, str)
            and not value.strip()
        ):
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
    def _validate_recipient_email(employee):
        """Return a normalised employee email address."""

        email_address = getattr(
            employee,
            "email",
            None,
        )

        if not email_address:
            raise MissingEmployeeEmailError(
                "This employee does not have an email "
                "address."
            )

        email_address = str(
            email_address
        ).strip()

        if not email_address:
            raise MissingEmployeeEmailError(
                "This employee does not have an email "
                "address."
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
        """Return a verified generated payslip file path."""

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

        if (
            not file_path.exists()
            or not file_path.is_file()
        ):
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

        full_name = (
            f"{first_name} {last_name}"
        ).strip()

        return full_name or "Employee"

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

        return period_name or "Payroll Period"

    @classmethod
    def _build_message(
        cls,
        *,
        payslip,
        recipient_email,
        sender_email,
    ):
        """Create the payslip email and PDF attachment."""

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

        message = EmailMessage()

        message["Subject"] = (
            f"BUYOH Payslip — {period_name}"
        )

        message["From"] = sender_email
        message["To"] = recipient_email

        plain_text_body = (
            f"Dear {employee_name},\n\n"
            f"Please find attached your payslip for "
            f"{period_name}.\n\n"
            f"Please keep this document confidential.\n\n"
            f"Regards,\n"
            f"BUYOH Payroll"
        )

        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
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
                    border-radius: 8px;
                    overflow: hidden;
                "
            >
                <div
                    style="
                        background-color: #0d6efd;
                        color: #ffffff;
                        padding: 20px 24px;
                    "
                >
                    <h1
                        style="
                            margin: 0;
                            font-size: 22px;
                        "
                    >
                        BUYOH Payroll
                    </h1>
                </div>

                <div style="padding: 24px;">
                    <p>
                        Dear {employee_name},
                    </p>

                    <p>
                        Please find attached your payslip for
                        <strong>{period_name}</strong>.
                    </p>

                    <p>
                        Please keep this document confidential.
                    </p>

                    <p style="margin-top: 28px;">
                        Regards,<br>
                        <strong>BUYOH Payroll</strong>
                    </p>
                </div>

                <div
                    style="
                        padding: 14px 24px;
                        background-color: #f8f9fa;
                        color: #6c757d;
                        font-size: 12px;
                    "
                >
                    This email was generated automatically by
                    the BUYOH Payroll System.
                </div>
            </div>
        </body>
        </html>
        """

        message.set_content(
            plain_text_body
        )

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
    def _send_message(
        *,
        message,
        smtp_config,
    ):
        """Send a prepared email through the configured SMTP server."""

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

        Returns the normalised recipient email address after
        successful delivery.
        """

        employee = payslip.employee

        recipient_email = cls._validate_recipient_email(
            employee
        )

        smtp_config = cls._load_smtp_config()

        message = cls._build_message(
            payslip=payslip,
            recipient_email=recipient_email,
            sender_email=smtp_config["sender"],
        )

        employee_name = cls._employee_name(
            employee
        )

        period_name = cls._period_name(
            payslip
        )

        try:
            cls._send_message(
                message=message,
                smtp_config=smtp_config,
            )

        except EmailServiceError as error:
            cls._log_failure(
                payslip=payslip,
                user_id=sent_by_user_id,
                ip_address=ip_address,
                recipient_email=recipient_email,
                employee_name=employee_name,
                period_name=period_name,
                error_message=str(error),
            )

            raise

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

        return recipient_email

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
