from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.faction import FactionScale

FACTION_SCALE = total(
    FactionScale,
    {
        FactionScale.BAND: Defined(
            "Band",
            checked_by=(),
            used_by=(
                "db.kind_concepts.society.BUILT_IN_ORGANISATIONS",
                "db.tables.factions.FactionProfileRow",
                "engine.factions.agenda.dues",
                "engine.factions.book.new_profile",
                "engine.factions.offshoots.found_offshoot",
            ),
        ),
        FactionScale.COMPANY: Defined(
            "Company",
            checked_by=(),
            used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "db.tables.society_kinds.OrganisationKindRow", "engine.factions.agenda.dues"),
        ),
        FactionScale.ORGANISATION: Defined(
            "Organisation", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "engine.factions.agenda.dues")
        ),
        FactionScale.NETWORK: Defined("Network", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "engine.factions.agenda.dues")),
    },
)
