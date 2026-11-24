from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.affliction import ChangeSign, CharmKind, CureKind

CHANGE_SIGN = total(
    ChangeSign,
    {
        ChangeSign.SEASON: Defined("Each season", checked_by=("engine.body.packages_w52.trigger_came",), used_by=()),
        ChangeSign.SKY_EVENT: Defined("A sign in the sky", checked_by=("engine.body.packages_w52.trigger_came",), used_by=()),
        ChangeSign.EMOTION: Defined("A strong feeling", checked_by=("engine.body.packages_w52.trigger_came",), used_by=()),
        ChangeSign.WORD: Defined("A spoken word", checked_by=(), used_by=()),
        ChangeSign.NONE: Defined(
            "Fixed for good",
            checked_by=("engine.body.afflictions.transformation_turns",),
            used_by=(
                "engine.body.afflictions.transformation_turns",
                "engine.body.packages_w52.change_body",
                "engine.body.packages_w52.shape_row",
                "engine.body.packages_w52.trigger_came",
            ),
        ),
    },
)

CHARM_KIND = total(
    CharmKind,
    {
        CharmKind.LOVE: Defined(
            "Love",
            checked_by=(),
            used_by=(
                "engine.body.packages_w52.bind_charm",
                "engine.body.packages_w52.broken_charm",
                "engine.body.packages_w52.renewed",
                "engine.body.packages_w52.shape_row",
            ),
        ),
        CharmKind.OBEDIENCE: Defined("Obedience", checked_by=("engine.body.packages_w52.bind_charm",), used_by=()),
        CharmKind.DEVOTION: Defined("Devotion", checked_by=("engine.body.packages_w52.bind_charm",), used_by=()),
    },
)

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
            checked_by=("engine.body.afflictions.cure", "engine.body.afflictions.try_cures"),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "catalog.effect_packages.SLEEP_CURES",
                "engine.body.afflictions.package_turns",
                "engine.body.afflictions.try_cures",
                "engine.phases.body._addiction",
            ),
        ),
        CureKind.QUEST: Defined(
            "Quest",
            checked_by=("engine.body.afflictions.try_cures",),
            used_by=(
                "catalog.effect_packages.PACKAGES",
                "catalog.effect_packages.SLEEP_CURES",
                "engine.body.afflictions.try_cures",
                "engine.mythic.heroquests.settle_souls",
            ),
        ),
        CureKind.DIVINE: Defined("Divine", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.divine_cure")),
        CureKind.POWER: Defined("Power", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.power_cure")),
        CureKind.SYMBIONT: Defined("Symbiont", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.symbiont_cure")),
        CureKind.TRANSFER: Defined("Transfer", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.transfer_cure")),
        CureKind.AUGMENT: Defined("Augment", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.augment_cure")),
        CureKind.RELEASE: Defined(
            "Release",
            checked_by=(),
            used_by=("catalog.effect_packages.PACKAGES", "catalog.effect_packages.SLEEP_CURES", "engine.body.afflictions.release_cure"),
        ),
        CureKind.SITE: Defined("Site", checked_by=(), used_by=("catalog.effect_packages.PACKAGES", "engine.body.afflictions.site_cure")),
    },
)
