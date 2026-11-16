from collections.abc import Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import LawArea
from aerona.engine.context import TickContext
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

K = FactionKind
AREA_LOBBIES: Mapping[LawArea, frozenset[FactionKind]] = total(
    LawArea,
    {
        LawArea.SUCCESSION: frozenset({K.NOBLE_COUNCIL, K.ESTATE, K.PARTY}),
        LawArea.PROPERTY: frozenset({K.NOBLE_COUNCIL, K.PEASANT_LEAGUE, K.MERCHANT_GUILD, K.CHARTERED_COMPANY}),
        LawArea.FISCAL: frozenset({K.MERCHANT_GUILD, K.FINANCIERS, K.CRAFT_GUILD, K.PEASANT_LEAGUE, K.SMUGGLING_RING}),
        LawArea.PENAL: frozenset({K.CRIME_FAMILY, K.THIEVES_GUILD, K.ASSASSINS, K.BANDITS}),
        LawArea.MILITARY: frozenset({K.WARRIOR_ORDER, K.MERCENARY_COMPANY, K.VETERANS}),
        LawArea.SOCIAL: frozenset({K.PRIESTHOOD, K.HOLY_ORDER, K.MOVEMENT, K.WORKERS_UNION, K.SOCIAL_CIRCLE}),
        LawArea.PUBLIC_HEALTH: frozenset({K.SCHOLARS_ACADEMY, K.ENGINEERS_SOCIETY, K.WORKERS_UNION}),
        LawArea.MAGIC: frozenset({K.MAGE_ORDER, K.SECRET_SOCIETY, K.PRIESTHOOD}),
        LawArea.CONSTITUTIONAL: frozenset({K.PARTY, K.MOVEMENT, K.REBELS, K.NOBLE_COUNCIL}),
    },
)
AREA_ORDER: Mapping[LawArea, int] = total(
    LawArea,
    {
        LawArea.SUCCESSION: 80,
        LawArea.PROPERTY: 100,
        LawArea.FISCAL: 110,
        LawArea.PENAL: 130,
        LawArea.MILITARY: 120,
        LawArea.SOCIAL: 80,
        LawArea.PUBLIC_HEALTH: 90,
        LawArea.MAGIC: 100,
        LawArea.CONSTITUTIONAL: 70,
    },
)


async def lobbies_of(ctx: TickContext, members: list[int]) -> dict[FactionKind, int]:
    rows = await ctx.session.execute(
        select(FactionProfileRow.kind, EntityRow)
        .join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id)
        .where(FactionProfileRow.home_entity_id.in_(members), EntityRow.status == EntityStatus.CANON)
    )
    found: dict[FactionKind, int] = {}
    for kind, faction in rows.all():
        found[kind] = max(found.get(kind, 0), stat_or(faction, "sway", 0))
    return found


def pressed(rules: Rules, area: LawArea, lobbies: Mapping[FactionKind, int]) -> int:
    sway = sum(value for kind, value in lobbies.items() if kind in AREA_LOBBIES[area])
    return min(PERCENT, sway) * rules.legislation.lobby_conflict_pct // PERCENT


def area_order(area: LawArea) -> float:
    return AREA_ORDER[area] / PERCENT
