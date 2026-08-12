"""PDF payslip generation services."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import (
    TA_CENTER,
    TA_LEFT,
    TA_RIGHT,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Payslip, PayrollRecord
from app.services.company_settings_service import (
    CompanySettingsService,
)


ZERO = Decimal("0.00")

PAYSLIP_PAGE_SIZE = (
    210 * mm,
    110 * mm,
)


class PayslipServiceError(Exception):
    """Base exception for payslip service failures."""


class PayslipRecordNotFoundError(PayslipServiceError):
    """Raised when the requested payroll record does not exist."""


class PayslipGenerationError(PayslipServiceError):
    """Raised when a payslip PDF cannot be generated or saved."""


class PayslipService:
    """Generate and persist employee payslip PDFs."""

    @staticmethod
    def _money(value):
        """Return a monetary value formatted to two decimal places."""

        if value is None:
            value = ZERO

        return f"{Decimal(str(value)):,.2f}"

    @staticmethod
    def _uses_uk_statutory_labels(payroll_record):
        """Identify UK calculations from the persisted PAYE snapshot."""

        return bool(
            str(getattr(payroll_record, "uk_tax_code", "") or "").strip()
        )

    @classmethod
    def _employee_social_security_label(cls, payroll_record):
        if cls._uses_uk_statutory_labels(payroll_record):
            return "National Insurance (NI)"
        return "NSSA Deduction"

    @classmethod
    def _employer_social_security_label(cls, payroll_record):
        if cls._uses_uk_statutory_labels(payroll_record):
            return "Employer National Insurance"
        return "Employer NSSA"

    @staticmethod
    def _safe_text(
        value,
        fallback="-",
    ):
        """Return readable XML-safe text for ReportLab paragraphs."""

        if value is None:
            return fallback

        text = str(value).strip()

        if not text:
            return fallback

        return escape(text)

    @staticmethod
    def _plain_text(
        value,
        fallback="",
    ):
        """Return plain text for direct canvas drawing."""

        if value is None:
            return fallback

        text = str(value).strip()

        return text or fallback

    @classmethod
    def _employee_name(cls, employee):
        """Return the employee's full display name."""

        full_name = getattr(
            employee,
            "full_name",
            None,
        )

        if full_name:
            return cls._safe_text(full_name)

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

        return cls._safe_text(
            f"{first_name} {last_name}".strip(),
            "Unknown Employee",
        )

    @classmethod
    def _employee_number(cls, employee):
        """Return the employee identifier."""

        return cls._safe_text(
            getattr(
                employee,
                "employee_number",
                None,
            )
        )

    @classmethod
    def _department_name(cls, employee):
        """Return the employee department name."""

        department = getattr(
            employee,
            "department",
            None,
        )

        if department is None:
            return "-"

        return cls._safe_text(
            getattr(
                department,
                "name",
                None,
            )
        )

    @classmethod
    def _job_title(cls, employee):
        """Return an available designation or job title."""

        possible_fields = (
            "job_title",
            "position",
            "designation",
        )

        for field_name in possible_fields:
            value = getattr(
                employee,
                field_name,
                None,
            )

            if value:
                return cls._safe_text(value)

        return "-"

    @staticmethod
    def _date_joined(employee):
        """Return the employee joining date when available."""

        possible_fields = (
            "date_joined",
            "hire_date",
            "employment_date",
        )

        for field_name in possible_fields:
            value = getattr(
                employee,
                field_name,
                None,
            )

            if value:
                return value.strftime(
                    "%d %B %Y"
                )

        return "-"

    @classmethod
    def _bank_name(cls, employee):
        """Return employee bank name when available."""

        possible_fields = (
            "bank_name",
            "bank",
        )

        for field_name in possible_fields:
            value = getattr(
                employee,
                field_name,
                None,
            )

            if value:
                return cls._safe_text(value)

        return "-"

    @classmethod
    def _bank_account(cls, employee):
        """Return the employee bank account when available."""

        possible_fields = (
            "bank_account_number",
            "account_number",
            "bank_account",
        )

        for field_name in possible_fields:
            value = getattr(
                employee,
                field_name,
                None,
            )

            if value:
                return cls._safe_text(value)

        return "-"

    @staticmethod
    def _get_payroll_record(payroll_record_id):
        """Load the payroll record and related information."""

        payroll_record = db.session.get(
            PayrollRecord,
            payroll_record_id,
        )

        if payroll_record is None:
            raise PayslipRecordNotFoundError(
                "The requested payroll record was not found."
            )

        return payroll_record

    @classmethod
    def _build_output_path(
        cls,
        payroll_record,
    ):
        """Create the output directory and readable PDF filename."""

        employee = payroll_record.employee
        period = payroll_record.payroll_period

        base_directory = (
            Path("instance")
            / "generated_payslips"
            / str(period.year)
            / f"{period.month:02d}"
        )

        base_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        employee_number = (
            cls._plain_text(
                getattr(
                    employee,
                    "employee_number",
                    None,
                ),
                "employee",
            )
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

        period_label = datetime(
            period.year,
            period.month,
            1,
        ).strftime("%B-%Y")

        filename = (
            f"Payslip_{employee_number}_"
            f"{period_label}.pdf"
        )

        return base_directory / filename

    @staticmethod
    def _company_name(company_profile):
        """Return the configured registered or display name."""

        company_name = str(
            company_profile.get(
                "company_name",
                "",
            )
            or ""
        ).strip()

        display_name = str(
            company_profile.get(
                "display_name",
                "",
            )
            or ""
        ).strip()

        return (
            company_name
            or display_name
            or "Company"
        )

    @staticmethod
    def _company_address(company_profile):
        """Return the preferred configured company address."""

        physical_address = str(
            company_profile.get(
                "physical_address",
                "",
            )
            or ""
        ).strip()

        postal_address = str(
            company_profile.get(
                "postal_address",
                "",
            )
            or ""
        ).strip()

        return (
            physical_address
            or postal_address
            or ""
        )

    @staticmethod
    def _currency_label(company_profile):
        """Return the configured payroll currency."""

        return str(
            company_profile.get(
                "currency",
                "",
            )
            or "USD"
        ).strip()

    @staticmethod
    def _payslip_footer(company_profile):
        """Return the configured payslip footer."""

        return str(
            company_profile.get(
                "payslip_footer",
                "",
            )
            or ""
        ).strip()

    @classmethod
    def _build_logo(
        cls,
        logo_path,
    ):
        """Create a proportionally scaled ReportLab logo."""

        if not logo_path:
            return None

        try:
            image_reader = ImageReader(
                str(logo_path)
            )

            original_width, original_height = (
                image_reader.getSize()
            )

            if (
                original_width <= 0
                or original_height <= 0
            ):
                return None

            maximum_width = 27 * mm
            maximum_height = 17 * mm

            scale = min(
                maximum_width / original_width,
                maximum_height / original_height,
            )

            logo = Image(
                str(logo_path),
                width=original_width * scale,
                height=original_height * scale,
            )

            logo.hAlign = "LEFT"

            return logo

        except (
            OSError,
            TypeError,
            ValueError,
        ):
            return None

    @classmethod
    def generate_payslip(
        cls,
        payroll_record_id,
        generated_by_user_id,
    ):
        """
        Generate a PDF payslip and save its metadata.

        Existing payslip metadata is updated so regeneration
        replaces the existing PDF instead of creating duplicates.
        """

        payroll_record = cls._get_payroll_record(
            payroll_record_id
        )

        output_path = cls._build_output_path(
            payroll_record
        )

        try:
            cls._create_pdf(
                payroll_record=payroll_record,
                output_path=output_path,
            )

            payslip = Payslip.query.filter_by(
                payroll_record_id=payroll_record.id
            ).first()

            if payslip is None:
                payslip = Payslip(
                    payroll_record_id=payroll_record.id,
                    employee_id=payroll_record.employee_id,
                    generated_by=generated_by_user_id,
                    file_path=str(output_path),
                )

                db.session.add(payslip)

            else:
                payslip.generated_by = (
                    generated_by_user_id
                )

                payslip.file_path = str(
                    output_path
                )

                payslip.generated_at = (
                    datetime.utcnow()
                )

            db.session.commit()

        except (
            OSError,
            SQLAlchemyError,
            TypeError,
            ValueError,
        ) as error:
            db.session.rollback()

            raise PayslipGenerationError(
                "The payslip could not be generated."
            ) from error

        return payslip

    @classmethod
    def _draw_page_footer(
        cls,
        canvas,
        _document,
        footer_text,
    ):
        """Draw the configured footer at the bottom of the page."""

        footer_text = cls._plain_text(
            footer_text,
            "",
        )

        if not footer_text:
            return

        canvas.saveState()

        page_width, _page_height = PAYSLIP_PAGE_SIZE

        footer_y = 2.2 * mm
        line_y = footer_y + 3.5 * mm

        canvas.setStrokeColor(
            colors.HexColor("#D6D9DD")
        )
        canvas.setLineWidth(0.35)

        canvas.line(
            8 * mm,
            line_y,
            page_width - 8 * mm,
            line_y,
        )

        canvas.setFillColor(
            colors.HexColor("#777777")
        )
        canvas.setFont(
            "Helvetica",
            5.2,
        )

        maximum_width = (
            page_width
            - (20 * mm)
        )

        fitted_footer = cls._fit_canvas_text(
            canvas=canvas,
            value=footer_text,
            font_name="Helvetica",
            font_size=5.2,
            maximum_width=maximum_width,
        )

        canvas.drawCentredString(
            page_width / 2,
            footer_y,
            fitted_footer,
        )

        canvas.restoreState()

    @staticmethod
    def _fit_canvas_text(
        canvas,
        value,
        font_name,
        font_size,
        maximum_width,
    ):
        """Shorten canvas text when it exceeds available width."""

        text = str(
            value or ""
        ).strip()

        if not text:
            return ""

        if (
            canvas.stringWidth(
                text,
                font_name,
                font_size,
            )
            <= maximum_width
        ):
            return text

        suffix = "..."

        while text:
            candidate = (
                text + suffix
            )

            if (
                canvas.stringWidth(
                    candidate,
                    font_name,
                    font_size,
                )
                <= maximum_width
            ):
                return candidate

            text = text[:-1]

        return suffix

    @classmethod
    def _create_pdf(
        cls,
        payroll_record,
        output_path,
    ):
        """Build the compact landscape payslip PDF."""

        employee = payroll_record.employee
        period = payroll_record.payroll_period

        company = (
            CompanySettingsService.get_company_profile()
        )

        company_name = cls._company_name(
            company
        )

        company_address = cls._company_address(
            company
        )

        currency_label = cls._currency_label(
            company
        )

        payslip_footer = cls._payslip_footer(
            company
        )

        logo_file_path = (
            CompanySettingsService.get_logo_file_path()
        )

        logo = cls._build_logo(
            logo_file_path
        )

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=PAYSLIP_PAGE_SIZE,
            rightMargin=5 * mm,
            leftMargin=5 * mm,
            topMargin=4 * mm,
            bottomMargin=8 * mm,
        )

        normal_style = ParagraphStyle(
            name="PayslipNormal",
            fontName="Helvetica",
            fontSize=6.2,
            leading=7.5,
            alignment=TA_LEFT,
        )

        bold_style = ParagraphStyle(
            name="PayslipBold",
            parent=normal_style,
            fontName="Helvetica-Bold",
        )

        title_style = ParagraphStyle(
            name="PayslipTitle",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
        )

        subtitle_style = ParagraphStyle(
            name="PayslipSubtitle",
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=9,
            alignment=TA_CENTER,
        )

        amount_style = ParagraphStyle(
            name="PayslipAmount",
            parent=normal_style,
            alignment=TA_RIGHT,
        )

        amount_bold_style = ParagraphStyle(
            name="PayslipAmountBold",
            parent=bold_style,
            alignment=TA_RIGHT,
        )

        centered_style = ParagraphStyle(
            name="PayslipCentered",
            parent=normal_style,
            alignment=TA_CENTER,
        )

        centered_bold_style = ParagraphStyle(
            name="PayslipCenteredBold",
            parent=bold_style,
            alignment=TA_CENTER,
        )

        net_pay_label_style = ParagraphStyle(
            name="NetPayLabel",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#163A72"),
        )

        net_pay_amount_style = ParagraphStyle(
            name="NetPayAmount",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#163A72"),
        )

        story = []

        heading_text = [
            Paragraph(
                cls._safe_text(
                    company_name,
                    "Company",
                ),
                title_style,
            )
        ]

        if company_address:
            heading_text.append(
                Paragraph(
                    cls._safe_text(
                        company_address,
                        "",
                    ),
                    centered_style,
                )
            )

        heading_text.append(
            Paragraph(
                (
                    "Payslip for the period of "
                    f"{cls._safe_text(period.period_name)}"
                ),
                subtitle_style,
            )
        )

        if logo:
            heading = Table(
                [
                    [
                        logo,
                        heading_text,
                        "",
                    ]
                ],
                colWidths=[
                    34 * mm,
                    132 * mm,
                    34 * mm,
                ],
            )

        else:
            heading = Table(
                [
                    [
                        heading_text,
                    ]
                ],
                colWidths=[
                    200 * mm,
                ],
            )

        heading_style_rules = [
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER",
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                1,
            ),
        ]

        if logo:
            heading_style_rules.extend(
                [
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (0, 0),
                        5 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (0, 0),
                        2 * mm,
                    ),
                ]
            )

        heading.setStyle(
            TableStyle(
                heading_style_rules
            )
        )

        story.append(heading)

        story.append(
            Spacer(
                1,
                1.5 * mm,
            )
        )

        payment_date = (
            period.payment_date.strftime(
                "%d %B %Y"
            )
            if period.payment_date
            else "-"
        )

        employee_details = [
            [
                Paragraph(
                    "Employee ID",
                    bold_style,
                ),
                Paragraph(
                    (
                        ": "
                        f"{cls._employee_number(employee)}"
                    ),
                    normal_style,
                ),
                Paragraph(
                    "Name",
                    bold_style,
                ),
                Paragraph(
                    (
                        ": "
                        f"{cls._employee_name(employee)}"
                    ),
                    normal_style,
                ),
            ],
            [
                Paragraph(
                    "Department",
                    bold_style,
                ),
                Paragraph(
                    (
                        ": "
                        f"{cls._department_name(employee)}"
                    ),
                    normal_style,
                ),
                Paragraph(
                    "Designation",
                    bold_style,
                ),
                Paragraph(
                    (
                        ": "
                        f"{cls._job_title(employee)}"
                    ),
                    normal_style,
                ),
            ],
            [
                Paragraph(
                    "Date of Joining",
                    bold_style,
                ),
                Paragraph(
                    (
                        ": "
                        f"{cls._date_joined(employee)}"
                    ),
                    normal_style,
                ),
                Paragraph(
                    "Payment Date",
                    bold_style,
                ),
                Paragraph(
                    f": {payment_date}",
                    normal_style,
                ),
            ],
            [
                Paragraph(
                    "Bank Name",
                    bold_style,
                ),
                Paragraph(
                    (
                        ": "
                        f"{cls._bank_name(employee)}"
                    ),
                    normal_style,
                ),
                Paragraph(
                    "Bank Account",
                    bold_style,
                ),
                Paragraph(
                    (
                        ": "
                        f"{cls._bank_account(employee)}"
                    ),
                    normal_style,
                ),
            ],
        ]

        detail_table = Table(
            employee_details,
            colWidths=[
                28 * mm,
                68 * mm,
                29 * mm,
                75 * mm,
            ],
        )

        detail_table.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        1,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        1,
                    ),
                ]
            )
        )

        story.append(detail_table)

        story.append(
            Spacer(
                1,
                1.5 * mm,
            )
        )

        earnings_rows = [
            (
                "Basic Salary",
                payroll_record.basic_salary,
            ),
            (
                "Overtime",
                payroll_record.overtime_amount,
            ),
        ]

        if getattr(payroll_record, "uk_ssp_amount", 0):
            earnings_rows.append(
                ("Statutory Sick Pay (SSP)", payroll_record.uk_ssp_amount)
            )

        if getattr(payroll_record, "uk_smp_amount", 0):
            earnings_rows.append(
                ("Statutory Maternity Pay (SMP)", payroll_record.uk_smp_amount)
            )

        if getattr(payroll_record, "uk_spp_amount", 0):
            earnings_rows.append(
                ("Statutory Paternity Pay (SPP)", payroll_record.uk_spp_amount)
            )

        if getattr(payroll_record, "uk_sap_amount", 0):
            earnings_rows.append(("Statutory Adoption Pay (SAP)", payroll_record.uk_sap_amount))

        if getattr(payroll_record, "uk_shpp_amount", 0):
            earnings_rows.append(("Statutory Shared Parental Pay (ShPP)", payroll_record.uk_shpp_amount))

        if getattr(payroll_record, "uk_spbp_amount", 0):
            earnings_rows.append(
                (
                    "Statutory Parental Bereavement Pay (SPBP)",
                    payroll_record.uk_spbp_amount,
                )
            )

        if getattr(payroll_record, "uk_sncp_amount", 0):
            earnings_rows.append(
                (
                    "Statutory Neonatal Care Pay (SNCP)",
                    payroll_record.uk_sncp_amount,
                )
            )

        earnings_rows.extend(
            (
                (
                    f"{item.allowance_type} (non-cash benefit)"
                    if item.earning_classification == "Taxable Benefit"
                    else item.allowance_type
                ),
                item.amount,
            )
            for item in payroll_record.allowances
        )

        deduction_rows = []

        if (
            not cls._uses_uk_statutory_labels(payroll_record)
            or payroll_record.aids_levy
        ):
            deduction_rows.append(
                ("AIDS Levy", payroll_record.aids_levy)
            )

        deduction_rows.append(
            (
                cls._employee_social_security_label(payroll_record),
                payroll_record.nssa,
            )
        )

        if payroll_record.irregular_paye:
            deduction_rows[0:0] = [
                ("PAYE — Regular", payroll_record.regular_paye),
                ("PAYE — Irregular", payroll_record.irregular_paye),
            ]
        else:
            deduction_rows.insert(0, ("PAYE", payroll_record.paye))

        deduction_rows.extend(
            (item.deduction_type, item.amount)
            for item in payroll_record.deductions
            if item.reduces_net_pay
        )

        maximum_rows = max(
            len(earnings_rows),
            len(deduction_rows),
        )

        financial_data = [
            [
                Paragraph(
                    "Earnings",
                    bold_style,
                ),
                Paragraph(
                    "Amount",
                    amount_bold_style,
                ),
                Paragraph(
                    "Deductions",
                    bold_style,
                ),
                Paragraph(
                    "Amount",
                    amount_bold_style,
                ),
            ]
        ]

        for row_index in range(
            maximum_rows
        ):
            earning_name = ""
            earning_amount = ""
            deduction_name = ""
            deduction_amount = ""

            if row_index < len(
                earnings_rows
            ):
                earning_name = (
                    earnings_rows[row_index][0]
                )

                earning_amount = cls._money(
                    earnings_rows[row_index][1]
                )

            if row_index < len(
                deduction_rows
            ):
                deduction_name = (
                    deduction_rows[row_index][0]
                )

                deduction_amount = cls._money(
                    deduction_rows[row_index][1]
                )

            financial_data.append(
                [
                    Paragraph(
                        earning_name,
                        normal_style,
                    ),
                    Paragraph(
                        earning_amount,
                        amount_style,
                    ),
                    Paragraph(
                        deduction_name,
                        normal_style,
                    ),
                    Paragraph(
                        deduction_amount,
                        amount_style,
                    ),
                ]
            )

        financial_data.extend(
            [
                [
                    Paragraph(
                        "Total Cash Earnings",
                        bold_style,
                    ),
                    Paragraph(
                        cls._money(
                            payroll_record.gross_pay
                        ),
                        amount_bold_style,
                    ),
                    Paragraph(
                        "Total Deductions",
                        bold_style,
                    ),
                    Paragraph(
                        cls._money(
                            payroll_record.total_deductions
                        ),
                        amount_bold_style,
                    ),
                ],
                [
                    Paragraph(
                        cls._employer_social_security_label(payroll_record),
                        bold_style,
                    ),
                    Paragraph(
                        cls._money(
                            payroll_record.employer_nssa
                        ),
                        amount_bold_style,
                    ),
                    Paragraph(
                        "",
                        bold_style,
                    ),
                    Paragraph(
                        "",
                        amount_bold_style,
                    ),
                ],
            ]
        )

        financial_table = Table(
            financial_data,
            colWidths=[
                61 * mm,
                39 * mm,
                61 * mm,
                39 * mm,
            ],
            repeatRows=1,
        )

        financial_table.setStyle(
            TableStyle(
                [
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.black,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.whitesmoke,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                ]
            )
        )

        story.append(financial_table)

        story.append(
            Spacer(
                1,
                1.3 * mm,
            )
        )

        net_pay_table = Table(
            [
                [
                    Paragraph(
                        "NET PAY",
                        net_pay_label_style,
                    ),
                    Paragraph(
                        (
                            f"{cls._safe_text(currency_label)} "
                            f"{cls._money(payroll_record.net_pay)}"
                        ),
                        net_pay_amount_style,
                    ),
                ]
            ],
            colWidths=[
                100 * mm,
                100 * mm,
            ],
        )

        net_pay_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#EAF3FF"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.8,
                        colors.HexColor("#163A72"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                ]
            )
        )

        story.append(net_pay_table)

        story.append(
            Spacer(
                1,
                1 * mm,
            )
        )

        currency_note = Paragraph(
            (
                "(All figures in "
                f"{cls._safe_text(currency_label)})"
            ),
            centered_bold_style,
        )

        story.append(currency_note)

        story.append(
            Spacer(
                1,
                2.3 * mm,
            )
        )

        signature_table = Table(
            [
                [
                    Paragraph(
                        "____________________________",
                        normal_style,
                    ),
                    "",
                    Paragraph(
                        "____________________________",
                        amount_style,
                    ),
                ],
                [
                    Paragraph(
                        "Employer's Signature",
                        normal_style,
                    ),
                    "",
                    Paragraph(
                        "Employee's Signature",
                        amount_style,
                    ),
                ],
            ],
            colWidths=[
                80 * mm,
                40 * mm,
                80 * mm,
            ],
        )

        signature_table.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "BOTTOM",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                ]
            )
        )

        story.append(signature_table)

        document.build(
            story,
            onFirstPage=lambda canvas, doc: (
                cls._draw_page_footer(
                    canvas,
                    doc,
                    payslip_footer,
                )
            ),
            onLaterPages=lambda canvas, doc: (
                cls._draw_page_footer(
                    canvas,
                    doc,
                    payslip_footer,
                )
            ),
        )
