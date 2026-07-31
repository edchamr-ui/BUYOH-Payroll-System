"""Centralised access to company and payroll settings."""

from pathlib import Path

from flask import (
    current_app,
    has_app_context,
    url_for,
)

from app.models import Setting


class CompanySettingsService:
    """
    Provide tenant-neutral company settings.

    All templates, PDFs, emails and exports should use this
    service instead of hardcoded company names or branding.
    """

    DEFAULTS = {
        "company_name": "Company",
        "trading_name": "",
        "registration_number": "",
        "tax_number": "",
        "nssa_employer_number": "",
        "physical_address": "",
        "postal_address": "",
        "phone": "",
        "email": "",
        "website": "",
        "currency": "USD",
        "payroll_country": "Zimbabwe",
        "default_payment_day": "25",
        "company_logo_path": "",
        "payslip_footer": (
            "This payslip is confidential and intended "
            "for the named employee only."
        ),
        "payslip_email_subject": (
            "Your payslip for {period_name}"
        ),
        "payslip_email_message": (
            "Dear {employee_name},\n\n"
            "Please find attached your payslip for "
            "{period_name}.\n\n"
            "Regards,\n"
            "{company_name}"
        ),
    }

    @classmethod
    def get_value(
        cls,
        setting_key,
        default=None,
    ):
        """Return one setting value with a neutral fallback."""

        fallback = (
            cls.DEFAULTS.get(
                setting_key,
                "",
            )
            if default is None
            else default
        )

        if not has_app_context():
            return fallback

        setting = Setting.query.filter_by(
            setting_key=setting_key
        ).first()

        if setting is None:
            return fallback

        value = setting.setting_value

        if value is None:
            return fallback

        if isinstance(value, str):
            value = value.strip()

        return value if value != "" else fallback

    @classmethod
    def get_optional_value(
        cls,
        setting_key,
    ):
        """Return an optional setting without applying a fallback."""

        if not has_app_context():
            return ""

        setting = Setting.query.filter_by(
            setting_key=setting_key
        ).first()

        if setting is None:
            return ""

        return str(
            setting.setting_value or ""
        ).strip()

    @classmethod
    def get_company_profile(cls):
        """Return the complete company profile for application use."""

        company_name = cls.get_value(
            "company_name"
        )

        trading_name = cls.get_optional_value(
            "trading_name"
        )

        display_name = (
            trading_name
            or company_name
            or "Company"
        )

        logo_path = cls.get_optional_value(
            "company_logo_path"
        )

        logo_url = cls._build_logo_url(
            logo_path
        )

        return {
            "company_name": company_name,
            "trading_name": trading_name,
            "display_name": display_name,
            "registration_number": (
                cls.get_optional_value(
                    "registration_number"
                )
            ),
            "tax_number": cls.get_optional_value(
                "tax_number"
            ),
            "nssa_employer_number": (
                cls.get_optional_value(
                    "nssa_employer_number"
                )
            ),
            "physical_address": (
                cls.get_optional_value(
                    "physical_address"
                )
            ),
            "postal_address": (
                cls.get_optional_value(
                    "postal_address"
                )
            ),
            "phone": cls.get_optional_value(
                "phone"
            ),
            "email": cls.get_optional_value(
                "email"
            ),
            "website": cls.get_optional_value(
                "website"
            ),
            "currency": cls.get_value(
                "currency",
                "USD",
            ),
            "payroll_country": cls.get_value(
                "payroll_country",
                "Zimbabwe",
            ),
            "default_payment_day": (
                cls.get_value(
                    "default_payment_day",
                    "25",
                )
            ),
            "company_logo_path": logo_path,
            "company_logo_url": logo_url,
            "payslip_footer": cls.get_value(
                "payslip_footer"
            ),
            "payslip_email_subject": cls.get_value(
                "payslip_email_subject"
            ),
            "payslip_email_message": cls.get_value(
                "payslip_email_message"
            ),
        }

    @classmethod
    def get_display_name(cls):
        """Return the preferred company display name."""

        return cls.get_company_profile()[
            "display_name"
        ]

    @classmethod
    def get_registered_name(cls):
        """Return the registered company name."""

        return cls.get_company_profile()[
            "company_name"
        ]

    @classmethod
    def get_currency(cls):
        """Return the configured payroll currency."""

        return cls.get_company_profile()[
            "currency"
        ]

    @classmethod
    def get_logo_path(cls):
        """Return the relative static logo path."""

        return cls.get_company_profile()[
            "company_logo_path"
        ]

    @classmethod
    def get_logo_file_path(cls):
        """Return the absolute filesystem path to the logo."""

        logo_path = cls.get_logo_path()

        if not logo_path or not has_app_context():
            return None

        static_directory = Path(
            current_app.static_folder
        ).resolve()

        candidate = (
            static_directory
            / logo_path
        ).resolve()

        try:
            candidate.relative_to(
                static_directory
            )

        except ValueError:
            return None

        if not candidate.is_file():
            return None

        return candidate

    @classmethod
    def format_email_subject(
        cls,
        *,
        employee_name,
        period_name,
    ):
        """Render the configured payslip email subject."""

        template = cls.get_value(
            "payslip_email_subject"
        )

        return cls._safe_format(
            template,
            employee_name=employee_name,
            period_name=period_name,
            company_name=cls.get_display_name(),
        )

    @classmethod
    def format_email_message(
        cls,
        *,
        employee_name,
        period_name,
    ):
        """Render the configured payslip email message."""

        template = cls.get_value(
            "payslip_email_message"
        )

        return cls._safe_format(
            template,
            employee_name=employee_name,
            period_name=period_name,
            company_name=cls.get_display_name(),
        )

    @staticmethod
    def _safe_format(
        template,
        **values,
    ):
        """Format a template without crashing on unknown placeholders."""

        class SafeDictionary(dict):
            def __missing__(self, key):
                return "{" + key + "}"

        return str(
            template or ""
        ).format_map(
            SafeDictionary(values)
        )

    @staticmethod
    def _build_logo_url(logo_path):
        """Return the public static URL for a configured logo."""

        if not logo_path or not has_app_context():
            return None

        try:
            return url_for(
                "static",
                filename=logo_path,
            )

        except RuntimeError:
            return None
