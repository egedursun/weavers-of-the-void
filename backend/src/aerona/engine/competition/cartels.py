from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.competition import CartelRow, MarketStructureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.write_guard import held
from aerona.domain.enums.competition import CartelAim, CompetitionClause, MarketForm
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.competition.clauses import clause_strength
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, give_coin, take_coin
from aerona.engine.factions.companies import realm_of
from aerona.engine.loops.delay import lagged
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record

DISCIPLINE_LOCK = "discipline"
FIRST_DISCIPLINE = 70
FIRST_SECRECY = 60
LEAGUE = 3


async def active_cartels(ctx: TickContext) -> list[CartelRow]:
    return list(await ctx.session.scalars(select(CartelRow).where(CartelRow.broken_epoch.is_(None)).order_by(CartelRow.id)))


async def cartel_over(ctx: TickContext, market_id: int, commodity: CommodityKind) -> CartelRow | None:
    for cartel in await active_cartels(ctx):
        if cartel.commodity is commodity and market_id in (cartel.markets or []):
            return cartel
    return None


async def form_cartel(
    ctx: TickContext, members: list[int], commodity: CommodityKind, *, markets: list[int], aim: CartelAim, terms: int, leader: int | None
) -> CartelRow:
    names = [entity.name for entity in [await ctx.session.get(EntityRow, node) for node in members[:2]] if entity is not None]
    cartel = CartelRow(
        name=f"the compact of {' and '.join(names)}" if names else "a compact of sellers",
        leader_node_id=leader if leader is not None else (members[0] if members else None),
        members=sorted(set(members)),
        markets=sorted(set(markets)),
        commodity=commodity,
        aim=aim,
        agreed_price=terms if aim is not CartelAim.QUOTA else 0,
        quota=terms if aim is CartelAim.QUOTA else 0,
        secrecy=FIRST_SECRECY,
        discipline=FIRST_DISCIPLINE,
        formed_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(cartel)
    await ctx.session.flush()
    await record(
        ctx,
        "market.cartel_formed",
        roles={IncidentRole.ACTOR: cartel.members, IncidentRole.PLACE: cartel.markets[0]} if cartel.markets else {IncidentRole.ACTOR: cartel.members},
        facts={"commodity": commodity, "aim": aim},
    )
    return cartel


async def maybe_form(ctx: TickContext, structure: MarketStructureRow) -> CartelRow | None:
    if structure.form is not MarketForm.FEW_SELLERS or await cartel_over(ctx, structure.market_entity_id, structure.commodity) is not None:
        return None
    sellers = sorted(((int(node), share) for node, share in (structure.sellers or {}).items()), key=lambda item: (-item[1], item[0]))[:LEAGUE]
    members = [node for node, _share in sellers if not held(node)]
    if len(members) < 2 or not ctx.rng(f"competition.cartel.{structure.id}.{ctx.epoch}").chance(ctx.rules.competition.cartel_form_chance_pct):
        return None
    return await form_cartel(ctx, members, structure.commodity, markets=[structure.market_entity_id], aim=CartelAim.PRICE, terms=0, leader=None)


async def break_cartel(ctx: TickContext, cartel: CartelRow, why: str) -> None:
    cartel.broken_epoch = ctx.epoch
    standing = [node for node in cartel.members or [] if await ctx.session.get(NodeRow, node) is not None]
    roles = {IncidentRole.SUBJECT: standing} if standing else {}
    await record(ctx, "market.cartel_broken", roles=roles, facts={"commodity": cartel.commodity, "why": why})


async def expose(ctx: TickContext, cartel: CartelRow) -> None:
    table = ctx.rules.competition
    cartel.exposed = True
    realm = await realm_of(ctx, cartel.markets[0]) if cartel.markets else None
    treasury = await ctx.session.get(EntityRow, realm) if realm is not None else None
    fined = 0
    for member_id in cartel.members or []:
        member = await ctx.session.get(EntityRow, member_id)
        if member is None or held(member.id):
            continue
        fine = round_half_up(await coin_of(ctx.session, ctx.rules, member) * table.cartel_fine_pct / PERCENT)
        if fine and await take_coin(ctx.session, ctx.rules, member, fine):
            fined += fine
            if treasury is not None:
                await give_coin(ctx.session, ctx.rules, treasury, fine)
        profile = await ctx.session.get(FactionProfileRow, member.id)
        if profile is not None and "reputation" not in (profile.locked or []):
            profile.reputation = clamp_int(profile.reputation - table.cartel_trust_loss, 0, PERCENT)
    roles = {IncidentRole.SUBJECT: cartel.members} | ({IncidentRole.AUTHORITY: realm} if realm is not None else {})
    await record(ctx, "market.cartel_exposed", roles=roles, facts={"commodity": cartel.commodity, "fines": fined})
    await break_cartel(ctx, cartel, "it was exposed under the ban on cartels")


async def tend_cartel(ctx: TickContext, cartel: CartelRow) -> str | None:
    table = ctx.rules.competition
    if any(held(node) for node in cartel.members or []):
        return None
    alive = [node for node in cartel.members or [] if (member := await ctx.session.get(EntityRow, node)) is not None and member.status is EntityStatus.CANON]
    if len(alive) < 2:
        await break_cartel(ctx, cartel, "too few of its members remain")
        return "broken"
    if DISCIPLINE_LOCK not in (cartel.locked or []):
        cartel.discipline = clamp_int(cartel.discipline - table.cartel_discipline_decay, 0, PERCENT)
    ban = await clause_strength(ctx, cartel.markets[0], CompetitionClause.CARTEL_BAN) if cartel.markets else 0
    if ban and ctx.rng(f"competition.expose.{cartel.id}.{ctx.epoch}").chance(ban * (PERCENT - cartel.secrecy) / PERCENT):
        await expose(ctx, cartel)
        return "exposed"
    discipline = await lagged(ctx, BalanceLoop.CARTEL_CHEATING, cartel.leader_node_id or alive[0], cartel.discipline, subject=cartel.id)
    if discipline < table.cheat_gain_threshold:
        await break_cartel(ctx, cartel, "a member sold below the agreed terms")
        return "broken"
    return None


async def tend_cartels(ctx: TickContext, structures: list[MarketStructureRow]) -> dict[str, int]:
    counts = {"formed": 0, "broken": 0, "exposed": 0}
    for structure in structures:
        counts["formed"] += 1 if await maybe_form(ctx, structure) is not None else 0
    for cartel in await active_cartels(ctx):
        outcome = await tend_cartel(ctx, cartel)
        if outcome is not None:
            counts[outcome] += 1
    return counts
