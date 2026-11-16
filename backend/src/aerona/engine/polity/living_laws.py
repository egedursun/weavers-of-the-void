from sqlalchemy import Select, func, or_, select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.living import LivingLineRow, LivingLineSourceRow, LivingProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.polity.book import Realm

Params = dict[str, int | str | bool]
LEAN = 25


def pick(value: int, low: str, middle: str, high: str) -> str:
    return high if value >= LEAN else low if value <= -LEAN else middle


def standing(values: dict[ValueAxis, int]) -> str:
    mercy, order = values.get(ValueAxis.MERCY, 0), values.get(ValueAxis.HIERARCHY, 0)
    return "citizen" if mercy >= LEAN and order < LEAN else "property" if order >= LEAN and mercy <= 0 else "ward" if mercy >= 0 else "servant"


async def counted(ctx: TickContext, query: Select[int]) -> int:
    return int(await ctx.session.scalar(query) or 0)


async def living_world_laws(ctx: TickContext, realm: Realm, values: dict[ValueAxis, int]) -> list[tuple[LawKind, Params]]:
    towns = list(realm.members)
    folk = select(EntityRow.id).where(or_(EntityRow.location_id.in_(towns), EntityRow.id.in_(towns)))
    found: list[tuple[LawKind, Params]] = []
    lines = await counted(
        ctx, select(func.count()).select_from(LivingLineRow).where(or_(LivingLineRow.owner_node_id.in_(folk), LivingLineRow.maker_node_id.in_(folk)))
    )
    alive = await counted(ctx, select(func.count()).select_from(LivingProfileRow).where(LivingProfileRow.thing_node_id.in_(folk)))
    if lines or alive:
        found.append((LawKind.LIVING_CRAFT_LAW, {"level": pick(-values.get(ValueAxis.PURITY, 0), "banned", "licensed", "free")}))
    persons = select(EntityRow.id).where(EntityRow.entity_type.in_([EntityType.MORTAL, EntityType.PEOPLE]))
    owned = select(LivingLineRow.id).where(or_(LivingLineRow.owner_node_id.in_(folk), LivingLineRow.maker_node_id.in_(folk)))
    germ = await counted(
        ctx,
        select(func.count()).select_from(LivingLineSourceRow).where(LivingLineSourceRow.line_id.in_(owned), LivingLineSourceRow.organism_node_id.in_(persons)),
    )
    if germ:
        found.append((LawKind.GERMLINE_LAW, {"level": pick(-values.get(ValueAxis.FAMILY, 0), "banned", "licensed", "free")}))
    clones = await counted(
        ctx,
        select(func.count()).select_from(BondRow).where(BondRow.kind == BondKind.CLONE_OF, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(folk)),
    )
    if clones:
        found.append((LawKind.CLONE_LAW, {"level": pick(-values.get(ValueAxis.TRADITION, 0), "banned", "licensed", "free")}))
        found.append((LawKind.CLONE_STATUS, {"status": standing(values)}))
    designed = await counted(
        ctx, select(func.count()).select_from(EntityFlagRow).where(EntityFlagRow.flag == EntityFlag.DESIGNED_PEOPLE, EntityFlagRow.entity_id.in_(folk))
    )
    if designed:
        found.append((LawKind.DESIGNED_STATUS, {"status": standing(values)}))
    return found
