from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.affliction import CureKind, Transmission

CURE_KIND = total(
    CureKind,
    {
        CureKind.RITE: Defined(
            "Rite", checked_by=("engine.body.afflictions.try_cures",), used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.try_cures")
        ),
        CureKind.TECHNIQUE: Defined(
            "Technique",
            checked_by=("engine.body.afflictions.other_cures",),
            used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.other_cures"),
        ),
        CureKind.MEDICINE: Defined(
            "Medicine",
            checked_by=("engine.body.afflictions.cure_steps", "engine.body.afflictions.try_cures"),
            used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.try_cures"),
        ),
        CureKind.TIME: Defined(
            "Time",
            checked_by=("engine.body.afflictions.try_cures",),
            used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.try_cures", "engine.phases.body._addiction"),
        ),
        CureKind.QUEST: Defined(
            "Quest",
            checked_by=("engine.body.afflictions.try_cures",),
            used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.try_cures", "engine.mythic.heroquests.settle_souls"),
        ),
        CureKind.DIVINE: Defined("Divine", checked_by=("engine.body.afflictions.WIDER_CURES",), used_by=("catalog.effect_packages.PACKAGES",)),
        CureKind.POWER: Defined("Power", checked_by=("engine.body.afflictions.WIDER_CURES",), used_by=("catalog.effect_packages.PACKAGES",)),
        CureKind.SYMBIONT: Defined("Symbiont", checked_by=("engine.body.afflictions.WIDER_CURES",), used_by=("catalog.effect_packages.PACKAGES",)),
        CureKind.TRANSFER: Defined("Transfer", checked_by=("engine.body.afflictions.WIDER_CURES",), used_by=("catalog.effect_packages.PACKAGES",)),
        CureKind.AUGMENT: Defined("Augment", checked_by=("engine.body.afflictions.WIDER_CURES",), used_by=("catalog.effect_packages.PACKAGES",)),
    },
)

TRANSMISSION = total(
    Transmission,
    {
        Transmission.CONTACT: Defined(
            "Contact",
            checked_by=("engine.body.afflictions.stage_effects",),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "engine.body.afflictions.stage_effects",
                "engine.ecology.beast_acts.CARRIED_BY",
                "engine.phases.body._marks",
            ),
        ),
        Transmission.BITE: Defined(
            "Bite",
            checked_by=("engine.body.afflictions.spread_by_bite",),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "engine.body.afflictions.spread_by_bite",
                "engine.ecology.beast_acts.CARRIED_BY",
                "engine.ecology.beast_acts.bite_someone",
            ),
        ),
        Transmission.INGESTION: Defined(
            "Ingestion",
            checked_by=(),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "engine.customs.intoxicants.habits",
                "engine.lore.items.dose",
                "engine.mortal.acts.vice",
                "engine.phases.body._addiction",
            ),
        ),
        Transmission.INHALATION: Defined("Inhalation", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.ecology.beast_acts.CARRIED_BY")),
        Transmission.BLOOD: Defined(
            "Blood", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.feed", "engine.ecology.beast_acts.CARRIED_BY")
        ),
        Transmission.CURSE: Defined(
            "Curse",
            checked_by=(
                "engine.transform.beings.cursed",
                "engine.transform.peoples.final_share",
                "prompts.tools.render.template_variables",
                "tools.son.influence.curse",
            ),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "engine.arcana.resistance.DISPELLED_BY",
                "engine.body.afflictions.blood_curse",
                "engine.body.afflictions.desecration_curse",
                "engine.dominion.curses.curse_desecrator",
                "engine.faith.souls.take_host",
                "engine.mythic.geasa.doom",
                "engine.mythic.geasa.doom_broken",
                "engine.mythic.heroquests.CURSED",
                "engine.phases.body._marks",
                "engine.sites.digs.suffer",
                "tools.son.influence.curse",
            ),
        ),
        Transmission.BIRTH: Defined(
            "Birth",
            checked_by=(),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "engine.body.afflictions.inherit",
                "engine.ecology.lineages.pass_to_beast",
                "engine.phases.births.bloodline_marks",
            ),
        ),
        Transmission.RITE: Defined(
            "Rite",
            checked_by=("engine.phases.body._marks",),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "engine.arcana.longevity.begin_longevity",
                "engine.arcana.resistance.DISPELLED_BY",
                "engine.lore.rites.backlash",
                "engine.mythic.heroquests.CURSED",
                "engine.mythic.heroquests.bestow",
                "engine.phases.body._marks",
            ),
        ),
        Transmission.GAZE: Defined("Gaze", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.ecology.beast_acts.CARRIED_BY")),
        Transmission.EXPERIENCE: Defined(
            "Experience",
            checked_by=(),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "engine.arcana.warping.settle_stage",
                "engine.body.afflictions.traumatise",
                "engine.ecology.beast_acts.CARRIED_BY",
                "engine.mythic.heroquests.fail",
                "engine.mythic.heroquests.settle_souls",
            ),
        ),
    },
)
