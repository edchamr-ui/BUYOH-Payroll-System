"""Payroll year creation and calendar-generation service."""

import calendar
from dataclasses import dataclass
from datetime import date

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import (
    PayrollPeriod,
    PayrollYear,
)


class PayrollYearError(Exception):
    """Base payroll-year service error."""


class PayrollYearAlreadyExistsError(PayrollYearError):
    """Raised when the selected payroll year already exists."""


class PayrollYearCreationError(PayrollYearError):
    """Raised when a payroll year cannot be created safely."""


@dataclass(frozen=True)
class PayrollYearCreationResult:
    """Return details about one created payroll year."""

    payroll_year: PayrollYear
    created_period_count: int


class PayrollYearService:
    """Create payroll years and monthly payroll calendars."""

    @staticmethod
    def _month_end(year, month):
        return calendar.monthrange(year, month)[1]

    @classmethod
    def _payment_date(
        cls,
        *,
        year,
        month,
        payment_day,
        clamp_to_month_end,
    ):
        month_end = cls._month_end(year, month)

        if payment_day <= month_end:
            return date(
                year,
                month,
                payment_day,
            )

        if clamp_to_month_end:
            return date(
                year,
                month,
                month_end,
            )

        raise PayrollYearCreationError(
            f"Payment day {payment_day} is invalid for "
            f"{calendar.month_name[month]} {year}."
        )

    @classmethod
    def create_year(
        cls,
        *,
        year,
        payment_day,
        created_by_user_id,
        clamp_payment_day=True,
    ):
        """Create one payroll year and all twelve Draft periods."""

        existing = PayrollYear.query.filter_by(
            year=year
        ).first()

        if existing is not None:
            raise PayrollYearAlreadyExistsError(
                f"Payroll year {year} already exists."
            )

        payroll_year = PayrollYear(
            year=year,
            status=PayrollYear.STATUS_OPEN,
            opened_by_user_id=created_by_user_id,
        )

        db.session.add(payroll_year)

        try:
            db.session.flush()

            for month in range(1, 13):
                month_end = cls._month_end(
                    year,
                    month,
                )

                period = PayrollPeriod(
                    payroll_year_id=payroll_year.id,
                    month=month,
                    year=year,
                    start_date=date(
                        year,
                        month,
                        1,
                    ),
                    end_date=date(
                        year,
                        month,
                        month_end,
                    ),
                    payment_date=cls._payment_date(
                        year=year,
                        month=month,
                        payment_day=payment_day,
                        clamp_to_month_end=(
                            clamp_payment_day
                        ),
                    ),
                    status="Draft",
                    created_by=created_by_user_id,
                )

                db.session.add(period)

            db.session.commit()

        except IntegrityError as error:
            db.session.rollback()

            raise PayrollYearCreationError(
                "The payroll year conflicts with existing "
                "payroll periods or year records."
            ) from error

        except SQLAlchemyError as error:
            db.session.rollback()

            raise PayrollYearCreationError(
                "The payroll year could not be created."
            ) from error

        return PayrollYearCreationResult(
            payroll_year=payroll_year,
            created_period_count=12,
        )

