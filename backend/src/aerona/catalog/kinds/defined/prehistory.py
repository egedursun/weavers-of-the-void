from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.prehistory import PrehistoryKind

PREHISTORY_KIND = total(
    PrehistoryKind,
    {
        PrehistoryKind.FULL: Defined(
            "The full run",
            checked_by=(),
            used_by=(
                "catalog.prehistory.SIMULATED_KINDS",
                "catalog.prehistory.WORLD_PREHISTORY",
                "db.tables.world_views.WorldViewRow",
                "engine.cosmos.world_views.WorldView",
                "engine.prehistory.digest.make_lost_origin",
            ),
        ),
        PrehistoryKind.LIVING: Defined(
            "The full run and the world's own moods",
            checked_by=("engine.prehistory.run.growth_phases",),
            used_by=("catalog.prehistory.SIMULATED_KINDS", "catalog.prehistory.SPECIAL_KINDS"),
        ),
        PrehistoryKind.SOULS: Defined("Arrival of the dead", checked_by=("engine.prehistory.run.derive",), used_by=("catalog.prehistory.SPECIAL_KINDS",)),
        PrehistoryKind.DREAMT: Defined(
            "A dreamt past", checked_by=("engine.phases.prehistory.dreamt_pasts", "engine.prehistory.run.derive"), used_by=("catalog.prehistory.SPECIAL_KINDS",)
        ),
        PrehistoryKind.MIRRORED: Defined(
            "The twin's past, mirrored",
            checked_by=("engine.prehistory.run.derive", "engine.prehistory.run.prepare"),
            used_by=("catalog.prehistory.SPECIAL_KINDS",),
        ),
        PrehistoryKind.PALACE: Defined(
            "The deeds of its god", checked_by=(), used_by=("catalog.life.prehistory.DERIVE_PREHISTORY_KINDS", "catalog.prehistory.SPECIAL_KINDS")
        ),
        PrehistoryKind.VOYAGE: Defined(
            "The voyage", checked_by=("engine.prehistory.run.derive", "engine.prehistory.run.prepare"), used_by=("catalog.prehistory.SPECIAL_KINDS",)
        ),
        PrehistoryKind.PHENOMENON: Defined(
            "The phenomenon it grew from", checked_by=("engine.prehistory.run.derive",), used_by=("catalog.prehistory.SPECIAL_KINDS",)
        ),
        PrehistoryKind.CORPSE: Defined(
            "The god's life, death and body",
            checked_by=(),
            used_by=("catalog.life.prehistory.DERIVE_PREHISTORY_KINDS", "catalog.prehistory.SIMULATED_KINDS", "catalog.prehistory.SPECIAL_KINDS"),
        ),
    },
)
