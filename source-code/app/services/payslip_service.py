"""PDF payslip generation services."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Payslip, PayrollRecord


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

    COMPANY_NAME = "BUYOH (Pvt) Ltd"
    COMPANY_ADDRESS = "Harare, Zimbabwe"
    CURRENCY_LABEL = "USD"

    @staticmethod
    def _money(value):
        """Return a monetary value formatted to two decimal places."""

        if value is None:
            value = ZERO

        return f"{Decimal(str(value)):,.2f}"

    @staticmethod
    def _safe_text(value, fallback="-"):
        """Return readable text for optional values."""

        if value is None:
            return fallback

        text = str(value).strip()

        return text or fallback

    @classmethod
    def _employee_name(cls, employee):
        """Return the employee's full display name."""

        full_name = getattr(employee, "full_name", None)

        if full_name:
            return str(full_name)

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

        return (
            f"{first_name} {last_name}".strip()
            or "Unknown Employee"
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

    @staticmethod
    def _job_title(employee):
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
                return str(value)

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

    @staticmethod
    def _bank_name(employee):
        """Return employee bank details when available."""

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
                return str(value)

        return "-"

    @staticmethod
    def _bank_account(employee):
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
                return str(value)

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
        """Create the output directory and PDF file path."""

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
            cls._employee_number(employee)
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

        filename = (
            f"payslip_{employee_number}_"
            f"{period.year}_{period.month:02d}.pdf"
        )

        return base_directory / filename

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
            ValueError,
        ) as error:
            db.session.rollback()

            raise PayslipGenerationError(
                "The payslip could not be generated."
            ) from error

        return payslip

    @classmethod
    def _create_pdf(
        cls,
        payroll_record,
        output_path,
    ):
        """Build the compact landscape payslip PDF."""

        employee = payroll_record.employee
        period = payroll_record.payroll_period

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=PAYSLIP_PAGE_SIZE,
            rightMargin=5 * mm,
            leftMargin=5 * mm,
            topMargin=4 * mm,
            bottomMargin=4 * mm,
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

        story = []

        heading = Table(
            [
                [
                    Paragraph(
                        cls.COMPANY_NAME,
                        title_style,
                    )
                ],
                [
                    Paragraph(
                        cls.COMPANY_ADDRESS,
                        centered_style,
                    )
                ],
                [
                    Paragraph(
                        (
                            "Payslip for the period of "
                            f"{period.period_name}"
                        ),
                        subtitle_style,
                    )
                ],
            ],
            colWidths=[
                200 * mm,
            ],
        )

        heading.setStyle(
            TableStyle(
                [
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
            )
        )

        story.append(heading)
        story.append(
            Spacer(
                1,
                2 * mm,
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
                2 * mm,
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
            (
                "Allowances",
                payroll_record.allowances_total,
            ),
        ]

        deduction_rows = [
            (
                "PAYE",
                payroll_record.paye,
            ),
            (
                "AIDS Levy",
                payroll_record.aids_levy,
            ),
            (
                "NSSA Deduction",
                payroll_record.nssa,
            ),
            (
                "Other Deductions",
                payroll_record.other_deductions_total,
            ),
        ]

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
                        "Total Earnings",
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
                        "Employer NSSA",
                        bold_style,
                    ),
                    Paragraph(
                        cls._money(
                            payroll_record.employer_nssa
                        ),
                        amount_bold_style,
                    ),
                    Paragraph(
                        "Net Pay",
                        bold_style,
                    ),
                    Paragraph(
                        cls._money(
                            payroll_record.net_pay
                        ),
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
                1.5 * mm,
            )
        )

        currency_note = Paragraph(
            (
                "(All figures in "
                f"{cls.CURRENCY_LABEL})"
            ),
            centered_bold_style,
        )

        story.append(currency_note)
        story.append(
            Spacer(
                1,
                4 * mm,
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

        document.build(story)
