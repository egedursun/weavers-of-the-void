from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.belonging import FugitiveKind, SalienceDriver, SanctuaryKind

FUGITIVE_KIND = total(
    FugitiveKind,
    {
        FugitiveKind.OUTLAW: Defined("Outlaw", checked_by=(), used_by=("engine.belonging.sanctuary.fugitives", "services.player.belonging.SanctuaryDraft")),
        FugitiveKind.ACCUSED: Defined("Accused", checked_by=(), used_by=("engine.belonging.sanctuary.fugitives",)),
        FugitiveKind.DEFECTOR: Defined("Defector", checked_by=(), used_by=("engine.belonging.sanctuary.asylums",)),
    },
)

SALIENCE_DRIVER = total(
    SalienceDriver,
    {
        SalienceDriver.BASELINE: Defined(
            "At rest",
            checked_by=(),
            used_by=("db.tables.belonging.HeldIdentityRow", "engine.belonging.identities.keep_identities", "engine.transform.peoples.identify"),
        ),
        SalienceDriver.HOLY_WAR: Defined("Holy war", checked_by=(), used_by=("engine.belonging.identities.war_pushes",)),
        SalienceDriver.FAMINE: Defined("Hunger", checked_by=(), used_by=("engine.belonging.identities.hunger_pushes",)),
        SalienceDriver.INVASION: Defined("Invasion", checked_by=(), used_by=("engine.belonging.identities.war_pushes",)),
        SalienceDriver.STRIKE: Defined("Strike", checked_by=(), used_by=("engine.belonging.identities.movement_pushes",)),
        SalienceDriver.RHETORIC: Defined("Preaching", checked_by=(), used_by=("engine.belonging.identities.movement_pushes",)),
        SalienceDriver.SEGREGATION: Defined("Kept apart", checked_by=(), used_by=("engine.belonging.identities.apart_pushes",)),
        SalienceDriver.CROSSING: Defined(
            "Mixed marriages", checked_by=(), used_by=("engine.belonging.identities.crossing_pushes", "engine.belonging.identities.guild_pushes")
        ),
        SalienceDriver.GOD: Defined("A god", checked_by=(), used_by=("services.player.belonging.HeldIdentityDraft", "tools.son.belonging.stir_identity")),
    },
)

SANCTUARY_KIND = total(
    SanctuaryKind,
    {
        SanctuaryKind.TEMPLE: Defined(
            "Temple sanctuary",
            checked_by=("engine.belonging.sanctuary.violate",),
            used_by=("engine.belonging.sanctuary.host_for", "services.player.belonging.SanctuaryDraft"),
        ),
        SanctuaryKind.HOSPITALITY: Defined("Guest right", checked_by=(), used_by=("engine.belonging.sanctuary.host_for",)),
        SanctuaryKind.ASYLUM: Defined("Asylum in a realm", checked_by=(), used_by=("engine.belonging.sanctuary.asylums",)),
    },
)
