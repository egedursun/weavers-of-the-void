from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.creator import CreatorHeresy

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
