from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.creator import CreatorHeresy, CreatorPassion

CREATOR_HERESY = total(
    CreatorHeresy,
    {
        CreatorHeresy.NONE: Defined(
            "No heresy",
            checked_by=("engine.divine.creator_bonds.keep_standing",),
            used_by=("db.tables.creator_bonds.CreatorStandingRow", "engine.divine.creator_bonds.heresy_for"),
        ),
        CreatorHeresy.ANTI_GOD: Defined("Against all gods", checked_by=(), used_by=("engine.divine.creator_bonds.heresy_for",)),
        CreatorHeresy.RIVAL_CREATOR: Defined("A rival maker", checked_by=(), used_by=("engine.divine.creator_bonds.heresy_for",)),
        CreatorHeresy.DENIAL: Defined(
            "There is no maker", checked_by=("engine.divine.creator_bonds.stance_for",), used_by=("engine.divine.creator_bonds.heresy_for",)
        ),
        CreatorHeresy.MANY_CREATORS: Defined("Many makers", checked_by=(), used_by=("engine.divine.creator_bonds.heresy_for",)),
        CreatorHeresy.ABSENT_CREATOR: Defined("The maker has gone", checked_by=(), used_by=("engine.divine.creator_bonds.heresy_for",)),
    },
)

CREATOR_PASSION = total(
    CreatorPassion,
    {
        CreatorPassion.ORDER: Defined(
            "Order",
            checked_by=("engine.gods.mood.passion_matches",),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS", "catalog.life.divine.TARGET_FOR_CREATOR_PASSIONS_2"),
        ),
        CreatorPassion.CHAOS: Defined(
            "Chaos",
            checked_by=("engine.divine.creator.passion_sign", "engine.gods.mood.passion_matches"),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS", "catalog.life.divine.TARGET_FOR_CREATOR_PASSIONS"),
        ),
        CreatorPassion.BEAUTY: Defined(
            "Beauty",
            checked_by=("engine.divine.creator.target_for", "engine.gods.mood.passion_matches"),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS"),
        ),
        CreatorPassion.KNOWLEDGE: Defined(
            "Knowledge",
            checked_by=("engine.divine.creator.passion_sign", "engine.divine.creator.target_for", "engine.gods.mood.passion_matches"),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS"),
        ),
        CreatorPassion.WAR: Defined(
            "War",
            checked_by=("engine.gods.mood.passion_matches",),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS", "catalog.life.divine.TARGET_FOR_CREATOR_PASSIONS"),
        ),
        CreatorPassion.MERCY: Defined(
            "Mercy",
            checked_by=("engine.divine.creator.target_for", "engine.gods.mood.passion_matches"),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS"),
        ),
        CreatorPassion.CREATION: Defined(
            "Creation",
            checked_by=("engine.gods.mood.passion_matches",),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS", "catalog.life.divine.TARGET_FOR_CREATOR_PASSIONS_2"),
        ),
        CreatorPassion.SILENCE: Defined(
            "Silence",
            checked_by=("engine.divine.creator.passion_sign", "engine.gods.mood.passion_matches"),
            used_by=("catalog.creator.CREATOR_PASSIONS", "engine.gods.reputation.read_passions"),
        ),
        CreatorPassion.FREEDOM: Defined(
            "Freedom",
            checked_by=("engine.divine.creator.freed_or_kept",),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS", "catalog.life.divine.KEPT_OR_FREED_PASSIONS"),
        ),
        CreatorPassion.MEMORY: Defined(
            "Memory",
            checked_by=(),
            used_by=("catalog.creator.ACTION_PASSIONS", "catalog.creator.CREATOR_PASSIONS", "catalog.life.divine.KEPT_OR_FREED_PASSIONS"),
        ),
    },
)
