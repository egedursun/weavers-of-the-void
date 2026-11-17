from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.mythic import GeasLayer, HeroquestBoon, OfficeChoice, QuestTrial

GEAS_LAYER = total(
    GeasLayer,
    {
        GeasLayer.SEER: Defined("A seer", checked_by=(), used_by=("engine.mythic.geasa.birth_geas",)),
        GeasLayer.GOD: Defined(
            "A god",
            checked_by=(),
            used_by=("db.tables.mythic.GeasRow", "engine.mythic.geasa.birth_geas", "services.player.mythic.GeasDraft", "tools.son.mythic.lay_geas"),
        ),
        GeasLayer.RITE: Defined("A rite", checked_by=(), used_by=("engine.lore.rites.bind_by_geas",)),
    },
)

HEROQUEST_BOON = total(
    HeroquestBoon,
    {
        HeroquestBoon.BLESSING: Defined("A blessing", checked_by=("engine.mythic.heroquests.bestow",), used_by=()),
        HeroquestBoon.ITEM: Defined("A magical item", checked_by=("engine.mythic.heroquests.bestow",), used_by=()),
        HeroquestBoon.RITE: Defined("A rite", checked_by=("engine.mythic.heroquests.bestow",), used_by=()),
        HeroquestBoon.LIFTED_CURSE: Defined("A lifted curse", checked_by=("engine.mythic.heroquests.bestow",), used_by=()),
        HeroquestBoon.RENEWED_LAND: Defined("A renewed land", checked_by=("engine.mythic.heroquests.renew",), used_by=()),
        HeroquestBoon.FAVOUR: Defined("The god's favour", checked_by=(), used_by=("engine.mythic.heroquests.bestow", "engine.mythic.heroquests.succeed")),
        HeroquestBoon.TRUE_NAME: Defined("A true name", checked_by=("engine.mythic.heroquests.bestow",), used_by=()),
        HeroquestBoon.TITLE: Defined("A title", checked_by=("engine.mythic.heroquests.bestow",), used_by=()),
    },
)

OFFICE_CHOICE = total(
    OfficeChoice,
    {
        OfficeChoice.COUNCIL: Defined("Chosen by the council", checked_by=(), used_by=("engine.divine.rulings.enact_appointment",)),
        OfficeChoice.CREATOR: Defined(
            "Given by the Creator",
            checked_by=(),
            used_by=(
                "api.routers.arcana.cosmic_offices",
                "db.tables.mythic.CosmicOfficeRow",
                "engine.mythic.control.seat_office",
                "engine.mythic.offices.offices",
            ),
        ),
        OfficeChoice.CONQUEST: Defined("Taken by conquest", checked_by=(), used_by=("engine.mythic.offices.conquer_offices",)),
        OfficeChoice.MANTLING: Defined("Taken by mantling", checked_by=(), used_by=("engine.mythic.mantling.replace",)),
    },
)

QUEST_TRIAL = total(
    QuestTrial,
    {
        QuestTrial.SKILL: Defined("A trial of skill", checked_by=(), used_by=("catalog.mythic.ARCHETYPE_TRIALS", "catalog.mythic.trial_at")),
        QuestTrial.PASSION: Defined("A trial of passion", checked_by=("engine.mythic.heroquests.trial_value",), used_by=("catalog.mythic.ARCHETYPE_TRIALS",)),
        QuestTrial.CONVICTION: Defined(
            "A trial of conviction", checked_by=("engine.mythic.heroquests.trial_value",), used_by=("catalog.mythic.ARCHETYPE_TRIALS",)
        ),
        QuestTrial.FAITH: Defined("A trial of faith", checked_by=("engine.mythic.heroquests.trial_value",), used_by=("catalog.mythic.ARCHETYPE_TRIALS",)),
    },
)
