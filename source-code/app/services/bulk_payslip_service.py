"""Bulk A4 payslip-book generation service."""

from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy.exc import SQLAlchemyError

from app.models import PayrollRecord
from app.services.company_settings_service import (
    CompanySettingsService,
)
from app.services.payslip_service import PayslipService


class BulkPayslipServiceError(Exception):
    """Base exception for bulk payslip generation failures."""


class NoPayrollRecordsError(BulkPayslipServiceError):
    """Raised when a payroll period has no payroll records."""


@dataclass(frozen=True)
class BulkPayslipResult:
    """Information about a successfully generated payslip book."""

    file_path: Path
    record_count: int
    page_count: int


class BulkPayslipService:
    """
    Generate a printable A4 payslip book.

    Each A4 portrait page contains up to three payslips,
    stacked vertically with cut guides between them.
    """

    PAGE_WIDTH, PAGE_HEIGHT = A4

    PAGE_MARGIN_X = 7 * mm
    PAGE_MARGIN_Y = 5 * mm

    PAYSLIPS_PER_PAGE = 3
    PAYSLIP_GAP = 3 * mm

    PAYSLIP_WIDTH = (
        PAGE_WIDTH
        - (2 * PAGE_MARGIN_X)
    )

    PAYSLIP_HEIGHT = (
        PAGE_HEIGHT
        - (2 * PAGE_MARGIN_Y)
        - (
            (PAYSLIPS_PER_PAGE - 1)
            * PAYSLIP_GAP
        )
    ) / PAYSLIPS_PER_PAGE

    @classmethod
    def generate_for_period(
        cls,
        payroll_period,
    ) -> BulkPayslipResult:
        """
        Generate one PDF containing all payslips for a period.

        The PDF contains three payslips per A4 portrait page.
        The final page may contain one, two, or three payslips.
        """

        records = (
            PayrollRecord.query
            .filter_by(
                payroll_period_id=payroll_period.id,
            )
            .order_by(
                PayrollRecord.employee_id.asc(),
                PayrollRecord.id.asc(),
            )
            .all()
        )

        if not records:
            raise NoPayrollRecordsError(
                "This payroll period has no payroll records."
            )

        output_path = cls._build_output_path(
            payroll_period=payroll_period,
        )

        try:
            page_count = cls._create_pdf(
                records=records,
                output_path=output_path,
            )

        except (
            OSError,
            SQLAlchemyError,
            TypeError,
            ValueError,
        ) as error:
            raise BulkPayslipServiceError(
                "The bulk payslip PDF could not be generated."
            ) from error

        return BulkPayslipResult(
            file_path=output_path,
            record_count=len(records),
            page_count=page_count,
        )

    @classmethod
    def _build_output_path(
        cls,
        payroll_period,
    ) -> Path:
        """Create the output directory and neutral PDF filename."""

        output_directory = (
            Path("instance")
            / "generated_payslips"
            / str(payroll_period.year)
            / f"{payroll_period.month:02d}"
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"all_payslips_"
            f"{payroll_period.year}_"
            f"{payroll_period.month:02d}.pdf"
        )

        return output_directory / filename

    @staticmethod
    def _company_profile():
        """Return the configured company profile."""

        return (
            CompanySettingsService.get_company_profile()
        )

    @classmethod
    def _company_name(
        cls,
        company_profile,
    ) -> str:
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

    @classmethod
    def _company_address(
        cls,
        company_profile,
    ) -> str:
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

    @classmethod
    def _currency_label(
        cls,
        company_profile,
    ) -> str:
        """Return the configured payroll currency."""

        return str(
            company_profile.get(
                "currency",
                "",
            )
            or "USD"
        ).strip()

    @classmethod
    def _payslip_footer(
        cls,
        company_profile,
    ) -> str:
        """Return the configured payslip footer."""

        return str(
            company_profile.get(
                "payslip_footer",
                "",
            )
            or ""
        ).strip()

    @classmethod
    def _create_pdf(
        cls,
        records: Sequence[PayrollRecord],
        output_path: Path,
    ) -> int:
        """Draw up to three payslips on each A4 portrait page."""

        company_profile = cls._company_profile()

        pdf = Canvas(
            str(output_path),
            pagesize=A4,
        )

        page_count = 0

        for record_index, payroll_record in enumerate(records):
            slot_index = (
                record_index
                % cls.PAYSLIPS_PER_PAGE
            )

            if slot_index == 0:
                page_count += 1

            payslip_top = (
                cls.PAGE_HEIGHT
                - cls.PAGE_MARGIN_Y
                - (
                    slot_index
                    * (
                        cls.PAYSLIP_HEIGHT
                        + cls.PAYSLIP_GAP
                    )
                )
            )

            payslip_bottom = (
                payslip_top
                - cls.PAYSLIP_HEIGHT
            )

            cls._draw_payslip(
                pdf=pdf,
                payroll_record=payroll_record,
                company_profile=company_profile,
                x=cls.PAGE_MARGIN_X,
                y=payslip_bottom,
                width=cls.PAYSLIP_WIDTH,
                height=cls.PAYSLIP_HEIGHT,
            )

            is_last_record = (
                record_index
                == len(records) - 1
            )

            is_last_slot = (
                slot_index
                == cls.PAYSLIPS_PER_PAGE - 1
            )

            if (
                not is_last_record
                and not is_last_slot
            ):
                cut_line_y = (
                    payslip_bottom
                    - (cls.PAYSLIP_GAP / 2)
                )

                cls._draw_cut_line(
                    pdf=pdf,
                    y=cut_line_y,
                )

            if is_last_slot or is_last_record:
                pdf.showPage()

        pdf.save()

        return page_count

    @classmethod
    def _draw_cut_line(
        cls,
        pdf: Canvas,
        y: float,
    ) -> None:
        """Draw a dashed cutting guide between payslips."""

        pdf.saveState()

        pdf.setStrokeColor(
            colors.HexColor("#777777")
        )
        pdf.setFillColor(
            colors.HexColor("#666666")
        )
        pdf.setLineWidth(0.35)
        pdf.setDash(3, 3)

        pdf.line(
            cls.PAGE_MARGIN_X,
            y,
            cls.PAGE_WIDTH - cls.PAGE_MARGIN_X,
            y,
        )

        pdf.setDash()
        pdf.setFont(
            "Helvetica",
            5,
        )

        pdf.drawCentredString(
            cls.PAGE_WIDTH / 2,
            y + 0.8 * mm,
            "CUT HERE",
        )

        pdf.restoreState()

    @classmethod
    def _draw_payslip(
        cls,
        pdf: Canvas,
        payroll_record: PayrollRecord,
        company_profile: dict,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Draw one complete payslip inside a fixed page slot."""

        employee = payroll_record.employee
        period = payroll_record.payroll_period

        pdf.saveState()

        pdf.setStrokeColor(colors.black)
        pdf.setFillColor(colors.black)
        pdf.setLineWidth(0.8)

        pdf.rect(
            x,
            y,
            width,
            height,
            stroke=1,
            fill=0,
        )

        inner_x = x + 3 * mm
        inner_width = width - 6 * mm
        top_y = y + height - 7 * mm

        cls._draw_header(
            pdf=pdf,
            period=period,
            company_profile=company_profile,
            x=inner_x,
            top_y=top_y,
            width=inner_width,
        )

        employee_details_top = (
            top_y - 15 * mm
        )

        cls._draw_employee_details(
            pdf=pdf,
            employee=employee,
            period=period,
            x=inner_x,
            top_y=employee_details_top,
            width=inner_width,
        )

        financial_table_top = (
            employee_details_top
            - 20 * mm
        )

        cls._draw_financial_table(
            pdf=pdf,
            payroll_record=payroll_record,
            x=inner_x,
            top_y=financial_table_top,
            width=inner_width,
        )

        cls._draw_footer(
            pdf=pdf,
            payroll_record=payroll_record,
            company_profile=company_profile,
            x=inner_x,
            y=y + 4 * mm,
            width=inner_width,
        )

        pdf.restoreState()

    @classmethod
    def _draw_header(
        cls,
        pdf: Canvas,
        period,
        company_profile: dict,
        x: float,
        top_y: float,
        width: float,
    ) -> None:
        """Draw the settings-driven company header."""

        company_name = unescape(
            cls._company_name(
                company_profile
            )
        )

        company_address = unescape(
            cls._company_address(
                company_profile
            )
        )

        logo_path = (
            CompanySettingsService.get_logo_file_path()
        )

        centre_x = (
            x + (width / 2)
        )

        if logo_path:
            cls._draw_logo(
                pdf=pdf,
                logo_path=logo_path,
                x=x,
                top_y=top_y,
            )

        pdf.setFillColor(
            colors.HexColor("#163A72")
        )
        pdf.setFont(
            "Helvetica-Bold",
            11,
        )

        fitted_company_name = cls._fit_text(
            pdf=pdf,
            value=company_name,
            font_name="Helvetica-Bold",
            font_size=11,
            maximum_width=width - 45 * mm,
        )

        pdf.drawCentredString(
            centre_x,
            top_y,
            fitted_company_name,
        )

        current_y = (
            top_y - 4 * mm
        )

        if company_address:
            pdf.setFillColor(colors.black)
            pdf.setFont(
                "Helvetica",
                5.8,
            )

            fitted_address = cls._fit_text(
                pdf=pdf,
                value=company_address,
                font_name="Helvetica",
                font_size=5.8,
                maximum_width=width - 45 * mm,
            )

            pdf.drawCentredString(
                centre_x,
                current_y,
                fitted_address,
            )

            current_y -= 4 * mm

        pdf.setFillColor(colors.black)
        pdf.setFont(
            "Helvetica-Bold",
            6.5,
        )

        period_name = unescape(
            PayslipService._safe_text(
                period.period_name
            )
        )

        pdf.drawCentredString(
            centre_x,
            current_y,
            f"PAYSLIP — {period_name}",
        )

        pdf.setLineWidth(0.4)

        pdf.line(
            x,
            top_y - 11 * mm,
            x + width,
            top_y - 11 * mm,
        )

    @classmethod
    def _draw_logo(
        cls,
        pdf: Canvas,
        logo_path: Path,
        x: float,
        top_y: float,
    ) -> None:
        """Draw the configured company logo in the header."""

        try:
            logo_reader = ImageReader(
                str(logo_path)
            )

            original_width, original_height = (
                logo_reader.getSize()
            )

            maximum_width = 25 * mm
            maximum_height = 11 * mm

            width_scale = (
                maximum_width
                / original_width
            )

            height_scale = (
                maximum_height
                / original_height
            )

            scale = min(
                width_scale,
                height_scale,
            )

            logo_width = (
                original_width
                * scale
            )

            logo_height = (
                original_height
                * scale
            )

            pdf.drawImage(
                logo_reader,
                x,
                top_y - logo_height + 2 * mm,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask="auto",
            )

        except (
            OSError,
            ValueError,
        ):
            return

    @classmethod
    def _draw_employee_details(
        cls,
        pdf: Canvas,
        employee,
        period,
        x: float,
        top_y: float,
        width: float,
    ) -> None:
        """Draw employee information in two compact columns."""

        left_label_x = x
        left_value_x = (
            x + 26 * mm
        )

        right_label_x = (
            x + (width / 2)
        )

        right_value_x = (
            right_label_x + 24 * mm
        )

        payment_date = (
            period.payment_date.strftime(
                "%d %B %Y"
            )
            if period.payment_date
            else "-"
        )

        left_rows = [
            (
                "Employee ID:",
                PayslipService._employee_number(
                    employee
                ),
            ),
            (
                "Department:",
                PayslipService._department_name(
                    employee
                ),
            ),
            (
                "Date Joined:",
                PayslipService._date_joined(
                    employee
                ),
            ),
            (
                "Pay Method:",
                PayslipService._safe_text(
                    getattr(
                        employee,
                        "payment_method",
                        None,
                    )
                ),
            ),
        ]

        right_rows = [
            (
                "Name:",
                PayslipService._employee_name(
                    employee
                ),
            ),
            (
                "Position:",
                PayslipService._job_title(
                    employee
                ),
            ),
            (
                "Pay Date:",
                payment_date,
            ),
            (
                "Bank / Account:",
                cls._bank_summary(
                    employee
                ),
            ),
        ]

        row_height = 4 * mm

        for row_index in range(4):
            row_y = (
                top_y
                - (row_index * row_height)
            )

            cls._draw_label_value(
                pdf=pdf,
                label=left_rows[row_index][0],
                value=left_rows[row_index][1],
                label_x=left_label_x,
                value_x=left_value_x,
                y=row_y,
                max_value_width=(
                    right_label_x
                    - left_value_x
                    - 3 * mm
                ),
            )

            cls._draw_label_value(
                pdf=pdf,
                label=right_rows[row_index][0],
                value=right_rows[row_index][1],
                label_x=right_label_x,
                value_x=right_value_x,
                y=row_y,
                max_value_width=(
                    x
                    + width
                    - right_value_x
                ),
            )

    @classmethod
    def _draw_label_value(
        cls,
        pdf: Canvas,
        label,
        value,
        label_x: float,
        value_x: float,
        y: float,
        max_value_width: float,
    ) -> None:
        """Draw one employee-information label and value."""

        pdf.setFont(
            "Helvetica-Bold",
            5.8,
        )

        pdf.drawString(
            label_x,
            y,
            str(label),
        )

        plain_value = unescape(
            str(
                value
                if value is not None
                else "-"
            )
        )

        fitted_value = cls._fit_text(
            pdf=pdf,
            value=plain_value,
            font_name="Helvetica",
            font_size=5.8,
            maximum_width=max_value_width,
        )

        pdf.setFont(
            "Helvetica",
            5.8,
        )

        pdf.drawString(
            value_x,
            y,
            fitted_value,
        )

    @classmethod
    def _draw_financial_table(
        cls,
        pdf: Canvas,
        payroll_record: PayrollRecord,
        x: float,
        top_y: float,
        width: float,
    ) -> None:
        """Draw earnings and deductions side by side."""

        half_width = (
            width / 2
        )

        amount_width = 24 * mm

        label_width = (
            half_width - amount_width
        )

        row_height = 4.2 * mm

        earnings = [
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
            (
                "",
                None,
            ),
        ]

        deductions = [
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

        table_rows = 6

        table_height = (
            table_rows * row_height
        )

        table_bottom = (
            top_y - table_height
        )

        pdf.setLineWidth(0.4)

        pdf.rect(
            x,
            table_bottom,
            width,
            table_height,
            stroke=1,
            fill=0,
        )

        vertical_positions = [
            x + label_width,
            x + half_width,
            x + half_width + label_width,
        ]

        for vertical_x in vertical_positions:
            pdf.line(
                vertical_x,
                table_bottom,
                vertical_x,
                top_y,
            )

        for row_index in range(
            1,
            table_rows,
        ):
            row_y = (
                top_y
                - (row_index * row_height)
            )

            pdf.line(
                x,
                row_y,
                x + width,
                row_y,
            )

        header_bottom = (
            top_y - row_height
        )

        pdf.setFillColor(
            colors.HexColor("#EFEFEF")
        )

        pdf.rect(
            x,
            header_bottom,
            width,
            row_height,
            stroke=0,
            fill=1,
        )

        pdf.setFillColor(colors.black)

        cls._draw_table_header(
            pdf=pdf,
            x=x,
            top_y=top_y,
            row_height=row_height,
            label_width=label_width,
            half_width=half_width,
            amount_width=amount_width,
        )

        for row_index in range(4):
            row_text_y = (
                top_y
                - (
                    (row_index + 1.72)
                    * row_height
                )
            )

            cls._draw_financial_row(
                pdf=pdf,
                label=earnings[row_index][0],
                amount=earnings[row_index][1],
                label_x=x + 1.2 * mm,
                amount_right=(
                    x
                    + half_width
                    - 1.2 * mm
                ),
                y=row_text_y,
            )

            cls._draw_financial_row(
                pdf=pdf,
                label=deductions[row_index][0],
                amount=deductions[row_index][1],
                label_x=(
                    x
                    + half_width
                    + 1.2 * mm
                ),
                amount_right=(
                    x
                    + width
                    - 1.2 * mm
                ),
                y=row_text_y,
            )

        totals_y = (
            table_bottom
            + (row_height / 2)
            - 1.8
        )

        pdf.setFont(
            "Helvetica-Bold",
            5.8,
        )

        pdf.drawString(
            x + 1.2 * mm,
            totals_y,
            "Total Earnings",
        )

        pdf.drawRightString(
            x + half_width - 1.2 * mm,
            totals_y,
            PayslipService._money(
                payroll_record.gross_pay
            ),
        )

        pdf.drawString(
            x + half_width + 1.2 * mm,
            totals_y,
            "Total Deductions",
        )

        pdf.drawRightString(
            x + width - 1.2 * mm,
            totals_y,
            PayslipService._money(
                payroll_record.total_deductions
            ),
        )

    @classmethod
    def _draw_table_header(
        cls,
        pdf: Canvas,
        x: float,
        top_y: float,
        row_height: float,
        label_width: float,
        half_width: float,
        amount_width: float,
    ) -> None:
        """Draw earnings and deductions table headings."""

        header_y = (
            top_y
            - (row_height / 2)
            - 1.8
        )

        pdf.setFont(
            "Helvetica-Bold",
            5.8,
        )

        pdf.drawString(
            x + 1.2 * mm,
            header_y,
            "Earnings",
        )

        pdf.drawRightString(
            x
            + label_width
            + amount_width
            - 1.2 * mm,
            header_y,
            "Amount",
        )

        pdf.drawString(
            x
            + half_width
            + 1.2 * mm,
            header_y,
            "Deductions",
        )

        pdf.drawRightString(
            x
            + (2 * half_width)
            - 1.2 * mm,
            header_y,
            "Amount",
        )

    @classmethod
    def _draw_financial_row(
        cls,
        pdf: Canvas,
        label: str,
        amount,
        label_x: float,
        amount_right: float,
        y: float,
    ) -> None:
        """Draw one earnings or deductions table row."""

        pdf.setFont(
            "Helvetica",
            5.6,
        )

        pdf.drawString(
            label_x,
            y,
            unescape(
                str(label or "")
            ),
        )

        amount_text = ""

        if amount is not None:
            amount_text = (
                PayslipService._money(amount)
            )

        pdf.drawRightString(
            amount_right,
            y,
            amount_text,
        )

    @classmethod
    def _draw_footer(
        cls,
        pdf: Canvas,
        payroll_record: PayrollRecord,
        company_profile: dict,
        x: float,
        y: float,
        width: float,
    ) -> None:
        """Draw net pay, signatures, and configured footer."""

        currency_label = unescape(
            cls._currency_label(
                company_profile
            )
        )

        payslip_footer = unescape(
            cls._payslip_footer(
                company_profile
            )
        )

        pdf.setFont(
            "Helvetica-Bold",
            7,
        )

        pdf.drawRightString(
            x + width,
            y + 11 * mm,
            (
                f"Net Pay: {currency_label} "
                f"{PayslipService._money(
                    payroll_record.net_pay
                )}"
            ),
        )

        signature_y = (
            y + 4.5 * mm
        )

        signature_width = 55 * mm

        left_signature_start = (
            x + 10 * mm
        )

        left_signature_end = (
            left_signature_start
            + signature_width
        )

        right_signature_end = (
            x + width - 10 * mm
        )

        right_signature_start = (
            right_signature_end
            - signature_width
        )

        pdf.setLineWidth(0.4)

        pdf.line(
            left_signature_start,
            signature_y,
            left_signature_end,
            signature_y,
        )

        pdf.line(
            right_signature_start,
            signature_y,
            right_signature_end,
            signature_y,
        )

        pdf.setFont(
            "Helvetica",
            5.2,
        )

        pdf.drawCentredString(
            (
                left_signature_start
                + left_signature_end
            ) / 2,
            signature_y - 2.8 * mm,
            "Employer's Signature",
        )

        pdf.drawCentredString(
            (
                right_signature_start
                + right_signature_end
            ) / 2,
            signature_y - 2.8 * mm,
            "Employee's Signature",
        )

        if payslip_footer:
            fitted_footer = cls._fit_text(
                pdf=pdf,
                value=payslip_footer,
                font_name="Helvetica",
                font_size=4.6,
                maximum_width=width,
            )

            pdf.setFillColor(
                colors.HexColor("#666666")
            )

            pdf.setFont(
                "Helvetica",
                4.6,
            )

            pdf.drawCentredString(
                x + (width / 2),
                y + 0.5 * mm,
                fitted_footer,
            )

            pdf.setFillColor(colors.black)

    @classmethod
    def _bank_summary(
        cls,
        employee,
    ) -> str:
        """Return a compact plain-text bank and account description."""

        bank_name = unescape(
            PayslipService._bank_name(
                employee
            )
        )

        account_number = unescape(
            PayslipService._bank_account(
                employee
            )
        )

        if (
            bank_name == "-"
            and account_number == "-"
        ):
            return "-"

        if bank_name == "-":
            return account_number

        if account_number == "-":
            return bank_name

        return (
            f"{bank_name} / {account_number}"
        )

    @staticmethod
    def _fit_text(
        pdf: Canvas,
        value,
        font_name: str,
        font_size: float,
        maximum_width: float,
    ) -> str:
        """Shorten a value only when it exceeds available width."""

        text = (
            unescape(
                str(value).strip()
            )
            if value is not None
            else "-"
        )

        if not text:
            return "-"

        if (
            pdf.stringWidth(
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
                pdf.stringWidth(
                    candidate,
                    font_name,
                    font_size,
                )
                <= maximum_width
            ):
                return candidate

            text = text[:-1]

        return suffix
