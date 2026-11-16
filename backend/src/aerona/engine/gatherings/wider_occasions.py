from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import AttendanceReason, GatheringKind, GuestRole
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.gatherings.occasions import Guest, Occasion, chance, living, structured

G = GatheringKind
INITIATING = frozenset({EntityType.FACTION})


async def mournings(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    ended = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.PAST, BondRow.closed_epoch == ctx.epoch))
    for bond in list(ended):
        ruler = await ctx.session.get(EntityRow, bond.source_node_id)
        realm = await living(ctx, bond.target_node_id)
        if ruler is None or realm is None or ruler.status is EntityStatus.CANON:
            continue
        profile = await ctx.session.get(PolityProfileRow, realm.id)
        seat = profile.capital_entity_id if profile is not None and profile.capital_entity_id is not None else realm.location_id
        found.append(Occasion(G.MOURNING, realm.id, realm.world_id, seat, ruler.id))
    return found


async def initiations(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    joined = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, BondRow.epoch == ctx.epoch))
    for bond in list(joined):
        order = await living(ctx, bond.target_node_id)
        newcomer = await living(ctx, bond.source_node_id)
        if order is None or newcomer is None or order.entity_type not in INITIATING:
            continue
        if chance(ctx, f"initiation.{bond.id}", ctx.rules.gatherings.initiation_pct):
            guests = [Guest(newcomer.id, GuestRole.HONOURED, AttendanceReason.OBLIGATION)]
            found.append(Occasion(G.INITIATION, order.id, order.world_id, order.location_id, newcomer.id, guests=guests))
    return found


async def summits_of_gods(ctx: TickContext) -> list[Occasion]:
    held_now = await ctx.session.scalar(select(ChronicleRow.id).where(ChronicleRow.kind == ChronicleKind.COUNCIL, ChronicleRow.epoch == ctx.epoch).limit(1))
    if held_now is None:
        return []
    sons = list(await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.level.desc(), SonRow.id)))
    if not sons:
        return []
    host = sons[0]
    guests = [Guest(son.id, GuestRole.GUEST, AttendanceReason.OBLIGATION) for son in sons[1:]]
    return [Occasion(G.SUMMIT_OF_GODS, host.id, host.current_world_id, None, guests=guests)]


async def network_gatherings(ctx: TickContext) -> list[Occasion]:
    members: dict[int, list[int]] = {}
    for network_id, member in await ctx.session.execute(select(NetworkNodeRow.network_entity_id, NetworkNodeRow.member_node_id).order_by(NetworkNodeRow.id)):
        members.setdefault(network_id, []).append(member)
    found: list[Occasion] = []
    for network_id, joined in sorted(members.items()):
        network = await living(ctx, network_id)
        if network is None or len(joined) < 2 or not chance(ctx, f"network.{network_id}", ctx.rules.gatherings.network_gathering_pct):
            continue
        guests = [Guest(member, GuestRole.GUEST, AttendanceReason.OBLIGATION) for member in joined if await living(ctx, member) is not None]
        found.append(Occasion(G.NETWORK_GATHERING, network.id, network.world_id, network.location_id, guests=guests))
    return found


async def realm_gatherings(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    realms = await ctx.session.scalars(select(MadeRealmRow).where(MadeRealmRow.keeper_node_id.is_not(None), MadeRealmRow.sealed.is_(False)))
    for realm in list(realms):
        keeper = await living(ctx, realm.keeper_node_id)
        if keeper is not None and chance(ctx, f"realm.{realm.dimension_id}", ctx.rules.gatherings.realm_gathering_pct):
            found.append(Occasion(G.REALM_GATHERING, keeper.id, keeper.world_id, keeper.location_id))
    return found


async def wider_occasions(ctx: TickContext) -> list[Occasion]:
    table = ctx.rules.gatherings
    return [
        *await mournings(ctx),
        *await initiations(ctx),
        *await summits_of_gods(ctx),
        *await network_gatherings(ctx),
        *await realm_gatherings(ctx),
        *await structured(ctx, StructureKind.MUSEUM, G.EXHIBITION, table.exhibition_pct),
        *await structured(ctx, StructureKind.GALLERY, G.EXHIBITION, table.exhibition_pct),
        *await structured(ctx, StructureKind.EXCHANGE, G.TRADE_FAIR, table.trade_fair_pct),
        *await structured(ctx, StructureKind.GUILDHALL, G.TRADE_FAIR, table.trade_fair_pct),
        *await structured(ctx, StructureKind.STADIUM, G.SPORT_MATCH, table.sport_match_pct),
    ]
