"""Combined built-in statutory preset catalogue."""

from app.statutory_data.botswana import BOTSWANA_PRESETS
from app.statutory_data.kenya import KENYA_PRESETS
from app.statutory_data.namibia import NAMIBIA_PRESETS
from app.statutory_data.south_africa import SOUTH_AFRICA_PRESETS
from app.statutory_data.zambia import ZAMBIA_PRESETS
from app.statutory_data.zimbabwe import ZIMBABWE_PRESETS


BUILTIN_PRESETS = [
    *ZIMBABWE_PRESETS,
    *ZAMBIA_PRESETS,
    *BOTSWANA_PRESETS,
    *NAMIBIA_PRESETS,
    *SOUTH_AFRICA_PRESETS,
    *KENYA_PRESETS,
]
