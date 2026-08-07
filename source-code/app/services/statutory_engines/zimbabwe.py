"""Zimbabwe statutory payroll engine."""

from app.services.statutory_engines.progressive import (
    ProgressivePayeEngine,
)


class ZimbabweStatutoryEngine(ProgressivePayeEngine):
    """Calculate Zimbabwe PAYE, NSSA and AIDS levy."""

    engine_key = "ZIMBABWE_PROGRESSIVE"
    country_code = "ZW"

    aliases = (
        "ZIMBABWE",
        "ZW",
        "ZW_PROGRESSIVE",
        "ZIMBABWE_PAYE",
    )

    contribution_labels = {
        "employee": "NSSA Employee",
        "employer": "NSSA Employer",
        "levy": "AIDS Levy",
    }
