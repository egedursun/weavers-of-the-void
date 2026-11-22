from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.life.polity import AREA_LOBBIES, AREA_ORDER
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import LawArea
from aerona.engine.context import TickContext
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules


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
