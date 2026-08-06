"""Shared helpers for statutory payroll settings."""

from decimal import Decimal

from sqlalchemy import and_, or_

from app.extensions import db
from app.models import (
    PayrollRecord,
    StatutoryRuleSet,
    TaxBand,
)
from app.services.statutory_library_service import (
    StatutoryLibraryService,
)


ONE_HUNDRED = Decimal("100")


def percentage_to_rate(value):
    """Convert a displayed percentage into a decimal rate."""

    if value is None:
        return Decimal("0")

    return (
        Decimal(str(value))
        / ONE_HUNDRED
    )


def rate_to_percentage(value):
    """Convert a stored decimal rate into a displayed percentage."""

    if value is None:
        return Decimal("0")

    return (
        Decimal(str(value))
        * ONE_HUNDRED
    )


def populate_rule_set_form(
    form,
    rule_set,
):
    """Populate the statutory rule-set edit form."""

    form.rule_set_id.data = str(
        rule_set.id
    )

    form.name.data = rule_set.name
    form.currency.data = rule_set.currency

    form.effective_from.data = (
        rule_set.effective_from
    )

    form.effective_to.data = (
        rule_set.effective_to
    )

    form.nssa_employee_percentage.data = (
        rate_to_percentage(
            rule_set.nssa_employee_rate
        )
    )

    form.nssa_employer_percentage.data = (
        rate_to_percentage(
            rule_set.nssa_employer_rate
        )
    )

    form.nssa_monthly_ceiling.data = (
        rule_set.nssa_monthly_ceiling
    )

    form.aids_levy_percentage.data = (
        rate_to_percentage(
            rule_set.aids_levy_rate
        )
    )

    form.paye_enabled.data = (
        rule_set.paye_enabled
    )

    form.is_active.data = (
        rule_set.is_active
    )


def find_overlapping_rule(
    *,
    currency,
    effective_from,
    effective_to,
    exclude_rule_set_id=None,
):
    """Return another active rule set whose effective dates overlap."""

    query = (
        StatutoryRuleSet.query
        .filter(
            StatutoryRuleSet.currency
            == currency,
            StatutoryRuleSet.is_active.is_(
                True
            ),
        )
    )

    if exclude_rule_set_id is not None:
        query = query.filter(
            StatutoryRuleSet.id
            != exclude_rule_set_id
        )

    new_end_condition = (
        True
        if effective_to is None
        else (
            StatutoryRuleSet.effective_from
            <= effective_to
        )
    )

    existing_end_condition = or_(
        StatutoryRuleSet.effective_to.is_(
            None
        ),
        StatutoryRuleSet.effective_to
        >= effective_from,
    )

    return (
        query
        .filter(
            and_(
                new_end_condition,
                existing_end_condition,
            )
        )
        .first()
    )


def rule_used_by_payroll(
    rule_set,
):
    """
    Return whether payroll records fall within the rule-set period.

    PayrollRecord currently does not store rule_set_id directly, so
    the rule-set effective dates are checked conservatively.
    """

    from app.models import PayrollPeriod

    matching_period = (
        PayrollPeriod.query
        .join(
            PayrollRecord,
            PayrollRecord.payroll_period_id
            == PayrollPeriod.id,
        )
        .filter(
            PayrollPeriod.payment_date
            >= rule_set.effective_from,
        )
    )

    if rule_set.effective_to is not None:
        matching_period = matching_period.filter(
            PayrollPeriod.payment_date
            <= rule_set.effective_to
        )

    return (
        matching_period.first()
        is not None
    )


def populate_tax_band_form(
    form,
    tax_band,
):
    """Populate the tax-band edit form."""

    form.tax_band_id.data = str(
        tax_band.id
    )

    form.band_order.data = (
        tax_band.band_order
    )

    form.lower_limit.data = (
        tax_band.lower_limit
    )

    form.upper_limit.data = (
        tax_band.upper_limit
    )

    form.rate_percentage.data = (
        rate_to_percentage(
            tax_band.rate
        )
    )


def ordered_tax_bands(
    rule_set,
    exclude_tax_band_id=None,
):
    """Return tax bands ordered for validation."""

    query = TaxBand.query.filter_by(
        rule_set_id=rule_set.id
    )

    if exclude_tax_band_id is not None:
        query = query.filter(
            TaxBand.id
            != exclude_tax_band_id
        )

    return (
        query
        .order_by(
            TaxBand.band_order.asc(),
            TaxBand.lower_limit.asc(),
        )
        .all()
    )


def validate_tax_band_candidate(
    *,
    rule_set,
    band_order,
    lower_limit,
    upper_limit,
    exclude_tax_band_id=None,
):
    """Return a validation message for an invalid tax-band candidate."""

    existing_bands = ordered_tax_bands(
        rule_set=rule_set,
        exclude_tax_band_id=(
            exclude_tax_band_id
        ),
    )

    if any(
        band.band_order == band_order
        for band in existing_bands
    ):
        return (
            "Another tax band already uses "
            f"band order {band_order}."
        )

    if (
        upper_limit is None
        and any(
            band.upper_limit is None
            for band in existing_bands
        )
    ):
        return (
            "Only one open-ended tax band is "
            "allowed for a rule set."
        )

    for band in existing_bands:
        existing_lower = Decimal(
            str(band.lower_limit)
        )

        existing_upper = (
            Decimal(
                str(band.upper_limit)
            )
            if band.upper_limit is not None
            else None
        )

        candidate_ends_before_existing = (
            upper_limit is not None
            and upper_limit <= existing_lower
        )

        existing_ends_before_candidate = (
            existing_upper is not None
            and existing_upper <= lower_limit
        )

        if not (
            candidate_ends_before_existing
            or existing_ends_before_candidate
        ):
            return (
                "The proposed tax band overlaps "
                f"with band {band.band_order}."
            )

    return None


def validate_complete_band_structure(
    rule_set,
):
    """Validate a complete progressive PAYE band structure."""

    bands = ordered_tax_bands(
        rule_set=rule_set
    )

    if not bands:
        return (
            False,
            "No PAYE tax bands have been configured.",
        )

    if (
        Decimal(
            str(bands[0].lower_limit)
        )
        != Decimal("0")
    ):
        return (
            False,
            "The first PAYE tax band must start at 0.00.",
        )

    for index, band in enumerate(
        bands
    ):
        is_last = (
            index == len(bands) - 1
        )

        if (
            band.upper_limit is None
            and not is_last
        ):
            return (
                False,
                (
                    "Only the final PAYE tax band "
                    "may be open-ended."
                ),
            )

        if not is_last:
            next_band = bands[
                index + 1
            ]

            current_upper = Decimal(
                str(band.upper_limit)
            )

            next_lower = Decimal(
                str(next_band.lower_limit)
            )

            if current_upper != next_lower:
                return (
                    False,
                    (
                        f"Band {band.band_order} ends at "
                        f"{current_upper:.2f}, but band "
                        f"{next_band.band_order} begins at "
                        f"{next_lower:.2f}. Tax bands must "
                        "be contiguous with no gaps."
                    ),
                )

    if bands[-1].upper_limit is not None:
        return (
            False,
            (
                "The final PAYE tax band must "
                "have no upper limit."
            ),
        )

    return (
        True,
        "The PAYE tax-band structure is valid.",
    )


def next_tax_band_order(
    rule_set,
):
    """Return the next available tax-band order."""

    highest_order = (
        db.session.query(
            db.func.max(
                TaxBand.band_order
            )
        )
        .filter(
            TaxBand.rule_set_id
            == rule_set.id
        )
        .scalar()
    )

    return (
        int(highest_order or 0)
        + 1
    )


def configure_statutory_preset_choices(
    form,
):
    """Populate the verified statutory preset selector."""

    presets = (
        StatutoryLibraryService
        .list_presets()
    )

    form.preset_key.choices = [
        (
            preset.preset_key,
            preset.display_name,
        )
        for preset in presets
    ]
