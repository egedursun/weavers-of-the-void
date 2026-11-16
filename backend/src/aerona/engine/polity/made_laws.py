from sqlalchemy import func, select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import AugmentRow, FabricationRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.made.surveillance import capacity_of
from aerona.engine.polity.book import Realm

Params = dict[str, int | str | bool]
LEAN = 25
MADE_ORIGINS = (MindOrigin.MADE, MindOrigin.GROWN, MindOrigin.TRAINED, MindOrigin.COPIED, MindOrigin.MERGED, MindOrigin.DIVIDED, MindOrigin.AWAKENED)


def pick(value: int, low: str, middle: str, high: str) -> str:
    return high if value >= LEAN else low if value <= -LEAN else middle


async def made_world_laws(ctx: TickContext, realm: Realm, values: dict[ValueAxis, int]) -> list[tuple[LawKind, Params]]:
    lean = values.get
    towns = list(realm.members)
    folk = select(EntityRow.id).where(EntityRow.location_id.in_(towns))
    found: list[tuple[LawKind, Params]] = []
    made = int(await ctx.session.scalar(select(func.count()).where(MindProfileRow.node_id.in_(folk), MindProfileRow.origin.in_(MADE_ORIGINS))) or 0)
    if made:
        mercy, order = lean(ValueAxis.MERCY, 0), lean(ValueAxis.HIERARCHY, 0)
        status = "citizen" if mercy >= LEAN and order < LEAN else "property" if order >= LEAN and mercy <= 0 else "ward" if mercy >= 0 else "servant"
        found.append((LawKind.MIND_STATUS, {"status": status}))
        found.append((LawKind.ERASURE_LAW, {"level": pick(mercy, "permitted", "regulated", "killing")}))
    copies = int(await ctx.session.scalar(select(func.count()).where(MindProfileRow.node_id.in_(folk), MindProfileRow.origin == MindOrigin.COPIED)) or 0)
    states = int(await ctx.session.scalar(select(func.count()).where(MindStateRow.mind_node_id.in_(folk))) or 0)
    if copies or states:
        found.append((LawKind.COPY_LAW, {"level": pick(-lean(ValueAxis.TRADITION, 0), "banned", "licensed", "free")}))
        found.append((LawKind.COPY_SUCCESSION, {"rule": pick(lean(ValueAxis.KINSHIP, 0), "all_equal", "by_court", "first_only")}))
    if int(await ctx.session.scalar(select(func.count()).where(AugmentRow.bearer_node_id.in_(folk))) or 0):
        found.append((LawKind.AUGMENT_LAW, {"level": pick(-lean(ValueAxis.PURITY, 0), "banned", "licensed", "free")}))
    if int(await ctx.session.scalar(select(func.count()).where(NetworkNodeRow.member_node_id.in_(towns))) or 0):
        found.append((LawKind.NETWORK_LAW, {"level": pick(-lean(ValueAxis.HIERARCHY, 0), "state_owned", "licensed", "open")}))
    if await capacity_of(ctx, realm.entity.id):
        order = lean(ValueAxis.HIERARCHY, 0)
        found.append((LawKind.SURVEILLANCE_LAW, {"level": "total" if order >= LEAN * 2 else pick(order, "forbidden", "warranted", "broad")}))
    if int(await ctx.session.scalar(select(func.count()).where(FabricationRow.settlement_entity_id.in_(towns), FabricationRow.share_pct > 0)) or 0):
        found.append((LawKind.PROVISION_LAW, {"level": pick(lean(ValueAxis.MERCY, 0) - lean(ValueAxis.WEALTH, 0), "market", "ration", "universal")}))
    return found
