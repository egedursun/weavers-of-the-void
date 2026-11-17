from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.cosmography import PhenomenonEffect, PhenomenonPersistence, PhenomenonTarget, RiftWork

PHENOMENON_EFFECT = total(
    PhenomenonEffect,
    {
        PhenomenonEffect.INTENSIFY: Defined(
            "strengthens", checked_by=(), used_by=("api.schemas.cosmography.PhenomenonRecord", "catalog.cosmography.PHENOMENON_MODEL")
        ),
        PhenomenonEffect.DISTORT: Defined("bends", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.OPEN: Defined("opens", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.SURGE: Defined("surges", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.LINGER: Defined("lingers in", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.MOVE: Defined("moves", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.GROW: Defined("grows", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.SUPPRESS: Defined("holds back", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.REVEAL: Defined("reveals", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.EMIT: Defined("gives off", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonEffect.SPREAD: Defined("spreads through", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
    },
)

PHENOMENON_PERSISTENCE = total(
    PhenomenonPersistence,
    {
        PhenomenonPersistence.PASSING: Defined(
            "Passing", checked_by=("engine.cosmos.phenomena.phenomena_cycles",), used_by=("catalog.cosmography.PHENOMENON_MODEL",)
        ),
        PhenomenonPersistence.LASTING: Defined(
            "Lasting", checked_by=(), used_by=("api.schemas.cosmography.PhenomenonRecord", "catalog.cosmography.PHENOMENON_MODEL")
        ),
        PhenomenonPersistence.PERMANENT: Defined(
            "Fades only when fully warded", checked_by=("engine.cosmos.phenomena.phenomena_cycles",), used_by=("catalog.cosmography.PHENOMENON_MODEL",)
        ),
    },
)

PHENOMENON_TARGET = total(
    PhenomenonTarget,
    {
        PhenomenonTarget.WEATHER: Defined(
            "Weather", checked_by=(), used_by=("api.schemas.cosmography.PhenomenonRecord", "catalog.cosmography.PHENOMENON_MODEL")
        ),
        PhenomenonTarget.TIME: Defined("Time", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.BOUNDARY: Defined("The boundary of the cosmos", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.MAGIC: Defined("Magic", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.DIVINITY: Defined("Divine power", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.PERCEPTION: Defined("What is seen", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.MATTER: Defined("Matter", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.LIFE: Defined("Life", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.GRAVITY: Defined("Gravity", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.SOUND: Defined("Sound", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.LIGHT: Defined("Light", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
        PhenomenonTarget.THE_DEAD: Defined("The dead", checked_by=(), used_by=("catalog.cosmography.PHENOMENON_MODEL",)),
    },
)

RIFT_WORK = total(
    RiftWork,
    {
        RiftWork.NONE: Defined(
            "Left alone",
            checked_by=("engine.cosmos.rift_control.keep_claims",),
            used_by=("db.tables.rift_control.RiftControlRow", "services.player.thin_b.RiftControlSet"),
        ),
        RiftWork.SEALING: Defined("Being sealed", checked_by=("engine.cosmos.rift_control.work_on",), used_by=("engine.cosmos.rift_control.chosen_work",)),
        RiftWork.STABILISING: Defined(
            "Being steadied", checked_by=("engine.cosmos.rift_control.work_on",), used_by=("engine.cosmos.rift_control.chosen_work",)
        ),
        RiftWork.GATE: Defined("Gated for a toll", checked_by=("engine.cosmos.rift_control.work_on",), used_by=("engine.cosmos.rift_control.chosen_work",)),
    },
)
