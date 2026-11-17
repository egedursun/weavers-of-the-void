from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.genetics import DwellingTenure

DWELLING_TENURE = total(
    DwellingTenure,
    {
        DwellingTenure.OWNED: Defined("Owned", checked_by=(), used_by=("db.tables.households.DwellingRow", "engine.households.forms.tenure_for")),
        DwellingTenure.RENTED: Defined("Rented", checked_by=("engine.households.forms.keep_dwelling",), used_by=("engine.households.forms.CLASS_TENURE",)),
        DwellingTenure.GRANTED: Defined(
            "Granted for service", checked_by=("engine.households.forms.keep_dwelling",), used_by=("engine.households.forms.CLASS_TENURE",)
        ),
        DwellingTenure.SQUATTED: Defined("Squatted", checked_by=("engine.households.forms.keep_dwelling",), used_by=("engine.households.forms.CLASS_TENURE",)),
    },
)
