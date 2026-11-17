from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.operations import QuirkKind

QUIRK_KIND = total(
    QuirkKind,
    {
        QuirkKind.FEARS_DARK: Defined(
            "Fears the dark", checked_by=(), used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS", "engine.operations.expeditions.strain")
        ),
        QuirkKind.DARK_SIGHTED: Defined(
            "Sees in the dark",
            checked_by=(),
            used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS", "engine.operations.expeditions.danger_of"),
        ),
        QuirkKind.KNOWS_WAYS: Defined(
            "Knows the ways", checked_by=("engine.operations.expeditions.launch",), used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS")
        ),
        QuirkKind.EATS_ANYTHING: Defined(
            "Eats anything", checked_by=(), used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS", "engine.operations.expeditions.ration")
        ),
        QuirkKind.HARDY: Defined(
            "Hardy",
            checked_by=(),
            used_by=(
                "catalog.operations.QUIRKS",
                "catalog.operations.QUIRK_ORIGINS",
                "engine.operations.expeditions.expose",
                "services.player.operations.QuirkDraft",
            ),
        ),
        QuirkKind.FRAIL: Defined(
            "Frail", checked_by=(), used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS", "engine.operations.expeditions.expose")
        ),
        QuirkKind.JUMPY: Defined(
            "Jumpy", checked_by=(), used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS", "engine.operations.expeditions.camp")
        ),
        QuirkKind.STEADY_NERVES: Defined(
            "Steady nerves", checked_by=(), used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS", "engine.operations.expeditions.strain")
        ),
        QuirkKind.KEEN_EYED: Defined(
            "Keen-eyed", checked_by=(), used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS", "engine.operations.expeditions.Party.count")
        ),
        QuirkKind.HOMESICK: Defined(
            "Homesick",
            checked_by=("engine.operations.expeditions.keep_expeditions",),
            used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS", "engine.operations.expeditions.strain"),
        ),
        QuirkKind.RESTLESS: Defined(
            "Restless",
            checked_by=("engine.operations.expeditions.keep_expeditions",),
            used_by=("catalog.operations.QUIRKS", "catalog.operations.QUIRK_ORIGINS"),
        ),
        QuirkKind.LIGHT_FINGERED: Defined(
            "Light-fingered",
            checked_by=(),
            used_by=(
                "catalog.operations.QUIRKS",
                "catalog.operations.QUIRK_ORIGINS",
                "engine.operations.expeditions.arrive",
                "engine.operations.expeditions.strain",
            ),
        ),
    },
)
