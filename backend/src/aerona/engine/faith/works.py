from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultHoldingRow, RelicRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import HoldingKind, TenetKind
from aerona.domain.enums.mind import MemoryKind, PressureKind, ValueAxis
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.faith.book import Church
from aerona.engine.mind.book import pressures_of, values_for, write_pressures
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import add_district

HUNDRED = 100
SAINT_RENOWN = 60
CLERGY_SAINTS = (MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER)


def tithe(ctx: TickContext, church: Church) -> int:
    doctrine = church.doctrine
    if doctrine is None:
        return 0
    output = (stat(church.cult, "followers") or 0) * ctx.rules.tithes.output_per_100 / HUNDRED
    income = round_half_up(output * doctrine.tithe_rate / PERCENT)
    doctrine.treasury += income
    return income


async def holdings_of(ctx: TickContext, church: Church, kind: HoldingKind) -> list[CultHoldingRow]:
    statement = select(CultHoldingRow).where(CultHoldingRow.cult_entity_id == church.cult.id, CultHoldingRow.kind == kind)
    return list(await ctx.session.scalars(statement))


async def hold(ctx: TickContext, church: Church, entity_id: int, kind: HoldingKind) -> bool:
    if await ctx.session.get(CultHoldingRow, (church.cult.id, entity_id)) is not None:
        return False
    ctx.session.add(CultHoldingRow(cult_entity_id=church.cult.id, holding_entity_id=entity_id, kind=kind, since_epoch=ctx.epoch))
    return True


async def survey_holdings(ctx: TickContext, church: Church) -> int:
    added = 0
    homes = [member.id for member in church.members]
    for member in church.members:
        added += await hold(ctx, church, member.id, HoldingKind.LAND)
    if homes:
        temples = await ctx.session.scalars(
            select(EntityRow.id).where(EntityRow.engine_kind == EngineKind.TEMPLE, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(homes))
        )
        for temple in temples:
            added += await hold(ctx, church, temple, HoldingKind.TEMPLE)
    target = church.tenets.get(TenetKind.PILGRIMAGE_DUTY)
    if target is not None and target.target is not None and target.target.isdigit():
        added += await hold(ctx, church, int(target.target), HoldingKind.HOLY_PLACE)
    return added


async def build(ctx: TickContext, church: Church, kind: HoldingKind, knowledge: KnowledgeMap) -> EntityRow | None:
    held = {row.holding_entity_id for row in await holdings_of(ctx, church, kind)}
    for member in church.members:
        if member.entity_type is not EntityType.SETTLEMENT or member.id in held:
            continue
        if await ctx.session.get(SettlementProfileRow, member.id) is None:
            continue
        town = await town_of(ctx, member, knowledge)
        await add_district(ctx, town, DistrictKind.TEMPLE_QUARTER, material=BuildMaterial.STONE, son_id=church.god.id if church.god is not None else None)
        await hold(ctx, church, member.id, kind)
        return member
    return None


async def alms(ctx: TickContext, church: Church) -> int:
    relief = ctx.rules.tithes.alms_poverty
    eased = 0
    for member in church.members:
        pressures = await pressures_of(ctx.session, member.id)
        if pressures.get(PressureKind.POVERTY, 0) <= 0:
            continue
        pressures[PressureKind.POVERTY] = clamp_int(pressures[PressureKind.POVERTY] - relief, 0, PERCENT)
        await write_pressures(ctx.session, member.id, pressures)
        eased += 1
    return eased


async def spend(ctx: TickContext, church: Church, knowledge: KnowledgeMap) -> str | None:
    doctrine = church.doctrine
    table = ctx.rules.tithes
    if doctrine is None:
        return None
    if church.holds(TenetKind.ASCETICISM) and doctrine.treasury >= table.alms_cost:
        doctrine.treasury -= table.alms_cost
        return "alms" if await alms(ctx, church) else None
    if church.holds(TenetKind.MONASTIC_LEARNING) and doctrine.treasury >= table.monastery_cost and await build(ctx, church, HoldingKind.MONASTERY, knowledge):
        doctrine.treasury -= table.monastery_cost
        return "monastery"
    if doctrine.treasury >= table.temple_cost and await build(ctx, church, HoldingKind.TEMPLE, knowledge):
        doctrine.treasury -= table.temple_cost
        return "temple"
    if doctrine.treasury >= table.alms_cost:
        doctrine.treasury -= table.alms_cost
        return "alms" if await alms(ctx, church) else None
    return None


async def saints(ctx: TickContext, church: Church) -> list[EntityRow]:
    homes = [member.id for member in church.members]
    if not homes:
        return []
    known = set(await ctx.session.scalars(select(RelicRow.saint_entity_id).where(RelicRow.saint_entity_id.is_not(None))))
    dead = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.DEAD,
            EntityRow.end_epoch == ctx.epoch,
            EntityRow.location_id.in_(homes),
            EntityRow.mortal_role.in_(list(CLERGY_SAINTS)),
        )
        .order_by(EntityRow.id)
    )
    found = []
    for mortal in dead:
        piety = (await values_for(ctx.session, mortal.id)).get(ValueAxis.PIETY, 0)
        if mortal.id not in known and (piety >= SAINT_RENOWN or (stat(mortal, "charisma") or 0) >= SAINT_RENOWN):
            found.append(mortal)
    return found


async def canonise(ctx: TickContext, church: Church, saint: EntityRow, item: EntityRow | None = None) -> RelicRow:
    relic_id = item.id if item is not None else saint.id
    row = await ctx.session.get(RelicRow, relic_id)
    if row is None:
        row = RelicRow(
            item_entity_id=relic_id,
            saint_entity_id=saint.id,
            cult_entity_id=church.cult.id,
            shrine_entity_id=saint.location_id,
            sanctity=PERCENT // 2,
            pilgrims=0,
            canonised_epoch=ctx.epoch,
        )
        ctx.session.add(row)
    await hold(ctx, church, relic_id, HoldingKind.RELIC)
    return row


async def pilgrimage(ctx: TickContext, church: Church) -> tuple[int, int]:
    relics = list(await ctx.session.scalars(select(RelicRow).where(RelicRow.cult_entity_id == church.cult.id)))
    duty = church.holds(TenetKind.PILGRIMAGE_DUTY)
    followers = stat(church.cult, "followers") or 0
    pilgrims = 0
    income = 0
    for relic in relics:
        relic.pilgrims = round_half_up(followers * relic.sanctity / PERCENT / HUNDRED * (2 if duty else 1))
        pilgrims += relic.pilgrims
        income += relic.pilgrims // HUNDRED
    if church.doctrine is not None:
        church.doctrine.treasury += income
    return pilgrims, income


async def temple_quarters(ctx: TickContext, church: Church) -> int:
    homes = [member.id for member in church.members]
    if not homes:
        return 0
    rows = await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id.in_(homes), DistrictRow.kind == DistrictKind.TEMPLE_QUARTER))
    return sum(row.level for row in rows)


async def pilgrim_plague(ctx: TickContext, church: Church, atlas: RegionAtlas) -> int:
    relics = list(await ctx.session.scalars(select(RelicRow).where(RelicRow.cult_entity_id == church.cult.id, RelicRow.pilgrims > 0)))
    if not relics:
        return 0
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    homes = {atlas.top_region(member.id) for member in church.members} - {None}
    spread = 0
    for relic in relics:
        shrine = atlas.top_region(relic.shrine_entity_id) if relic.shrine_entity_id is not None else None
        if shrine is None:
            continue
        open_rows = select(OutbreakRow).where(OutbreakRow.region_entity_id == shrine, OutbreakRow.status != OutbreakStatus.ENDED)
        chance = min(PERCENT, relic.pilgrims // HUNDRED)
        for outbreak in list(await ctx.session.scalars(open_rows)):
            disease = await ctx.session.get(EntityRow, outbreak.disease_entity_id)
            for region in sorted(home for home in homes if home is not None and home != shrine):
                if disease is not None and ctx.rng(f"pilgrim_plague.{relic.item_entity_id}.{region}.{ctx.epoch}").chance(chance):
                    await open_outbreak(ctx, book, disease, region, path=SpreadPath.JOURNEY, severity=outbreak.severity // 2, source=outbreak)
                    spread += 1
    return spread


async def sacred_beasts(ctx: TickContext, church: Church) -> int:
    row = church.tenets.get(TenetKind.SACRED_SPECIES)
    if row is None or row.target is None or not row.target.isdigit():
        return 0
    hunters = await ctx.session.scalars(
        select(BondRow.source_node_id).where(BondRow.target_node_id == int(row.target), BondRow.kind == BondKind.HUNTS, BondRow.state == BondState.ACTIVE)
    )
    wronged = 0
    for hunter_id in list(hunters):
        hunter = await ctx.session.get(EntityRow, hunter_id)
        if hunter is None or hunter.entity_type is EntityType.SPECIES:
            continue
        for member in church.members:
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=member.id,
                subject_id=hunter.id,
                kind=MemoryKind.DESECRATED_HOLY,
                magnitude=-ctx.rules.doctrine.sacred_species_grievance,
                epoch=ctx.epoch,
                note="hunted the sacred beast",
            )
            wronged += 1
    return wronged
