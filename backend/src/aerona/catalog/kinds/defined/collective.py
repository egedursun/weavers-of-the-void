from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.collective import HeraldryHolderKind, MobEnd, MobTarget, SocialBias

HERALDRY_HOLDER_KIND = total(
    HeraldryHolderKind,
    {
        HeraldryHolderKind.HOUSE: Defined(
            "A house",
            checked_by=("engine.collective.control.ARMS_TYPES", "engine.collective.heraldry.grant_arms", "engine.collective.heraldry.sync_emblem"),
            used_by=("engine.collective.heraldry.difference", "engine.collective.heraldry.holders", "tools.mortal.ways_of_rule.take_arms"),
        ),
        HeraldryHolderKind.POLITY: Defined(
            "A realm",
            checked_by=("engine.collective.control.ARMS_TYPES", "engine.collective.heraldry.sync_emblem"),
            used_by=("engine.collective.heraldry.holders", "tools.mortal.ways_of_rule.take_arms"),
        ),
        HeraldryHolderKind.TITLE: Defined("A title", checked_by=("engine.collective.heraldry.sync_emblem",), used_by=("engine.collective.heraldry.holders",)),
        HeraldryHolderKind.ARMY: Defined("An army", checked_by=("engine.collective.control.ARMS_TYPES",), used_by=("engine.collective.heraldry.holders",)),
        HeraldryHolderKind.GUILD: Defined(
            "An association or order", checked_by=("engine.collective.control.ARMS_TYPES",), used_by=("engine.collective.heraldry.holders",)
        ),
        HeraldryHolderKind.COMPANY: Defined("A company", checked_by=("engine.collective.control.ARMS_TYPES",), used_by=("engine.collective.heraldry.holders",)),
        HeraldryHolderKind.ORDER: Defined("An order", checked_by=("engine.collective.control.ARMS_TYPES",), used_by=("engine.collective.heraldry.holders",)),
        HeraldryHolderKind.PEOPLE: Defined("A people", checked_by=("engine.collective.control.ARMS_TYPES",), used_by=("engine.collective.heraldry.holders",)),
    },
)

MOB_END = total(
    MobEnd,
    {
        MobEnd.FATIGUE: Defined(
            "Tired and went home", checked_by=(), used_by=("engine.collective.crowds.rage_mobs", "services.integrity.collective_links.mend_collective_links")
        ),
        MobEnd.FORCE: Defined("Broken by force", checked_by=(), used_by=("engine.collective.crowds.rage_mobs",)),
        MobEnd.CONCESSION: Defined("Given its demands", checked_by=(), used_by=("engine.collective.crowds.concede", "services.player.collective.MobDisperse")),
    },
)

MOB_TARGET = total(
    MobTarget,
    {
        MobTarget.DISTRICT: Defined(
            "A district",
            checked_by=("engine.collective.crowds.storm",),
            used_by=("catalog.collective.TRIGGERS", "engine.collective.crowds.raise_mob", "services.player.collective.MobDraft"),
        ),
        MobTarget.GRANARY: Defined("The granary", checked_by=("engine.collective.crowds.storm",), used_by=("catalog.collective.TRIGGERS",)),
        MobTarget.SCAPEGOAT: Defined(
            "A scapegoat", checked_by=("engine.collective.crowds.raise_mob", "engine.collective.crowds.storm"), used_by=("catalog.collective.TRIGGERS",)
        ),
        MobTarget.GATE: Defined("The gate", checked_by=("engine.collective.crowds.storm",), used_by=("catalog.collective.TRIGGERS",)),
        MobTarget.TEMPLE: Defined("The temple", checked_by=(), used_by=("catalog.collective.TRIGGERS",)),
        MobTarget.PALACE: Defined("The palace", checked_by=("engine.collective.crowds.storm",), used_by=("catalog.collective.TRIGGERS",)),
        MobTarget.WORKSHOP: Defined("The workshops", checked_by=("engine.collective.crowds.storm",), used_by=("catalog.collective.TRIGGERS",)),
    },
)

SOCIAL_BIAS = total(
    SocialBias,
    {
        SocialBias.PRESTIGE: Defined("Copies the renowned", checked_by=("engine.collective.learning.learn_in",), used_by=()),
        SocialBias.CONFORMITY: Defined("Copies the many", checked_by=("engine.collective.learning.learn_in",), used_by=()),
        SocialBias.CONTENT: Defined("Copies the gripping", checked_by=("engine.collective.learning.learn_in",), used_by=()),
    },
)
