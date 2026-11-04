from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import GoodsFlowRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultHoldingRow, RelicRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CurseKind, ItemClass
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.economy import GOODS_SOURCES, CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import HoldingKind, TenetKind
from aerona.domain.enums.mind import MemoryKind, PressureKind, ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.economy.stocks import goods_of
from aerona.engine.faith.book import Church
from aerona.engine.gods.devotion import add_devotion
from aerona.engine.mind.book import pressures_of, values_for, write_pressures
from aerona.engine.mind.memories import remember
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import add_district

CLERGY_SAINTS = (MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER)
POOR = (SocialClass.FARMER, SocialClass.SERF_OR_SLAVE, SocialClass.OUTCAST)
THOUSAND = 1000


def credit(doctrine: CultDoctrineRow, amount: int) -> int:
    if "treasury" in doctrine.locked or amount == 0:
        return 0
    before = doctrine.treasury
    doctrine.treasury = max(0, doctrine.treasury + amount)
    return doctrine.treasury - before


def affordable(doctrine: CultDoctrineRow, cost: int) -> bool:
    return doctrine.treasury >= cost


async def realm_of(ctx: TickContext, community_id: int) -> PolityProfileRow | None:
    realm_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    return await ctx.session.get(PolityProfileRow, realm_id) if realm_id is not None else None


async def tithe_terms(ctx: TickContext, church: Church, laws: LawBook, community_id: int) -> tuple[int, int]:
    doctrine = church.doctrine
    rate = doctrine.tithe_rate if doctrine is not None else ctx.rules.tithes.rate
    realm = await realm_of(ctx, community_id)
    law = laws.in_force(realm.polity_entity_id, LawKind.TITHE) if realm is not None and realm.state_religion_id == church.cult.id else None
    if law is None or not bool(law.params.get("enforced")):
        return rate, ctx.rules.tithes.voluntary_pct
    if doctrine is not None and "tithe_rate" not in doctrine.locked:
        doctrine.tithe_rate = clamp_int(int(law.params.get("rate", rate)), 0, PERCENT)
        rate = doctrine.tithe_rate
    return rate, law.enforcement


async def output_of(ctx: TickContext, community_id: int) -> dict[CommodityKind, int]:
    rows = await ctx.session.scalars(
        select(GoodsFlowRow).where(
            GoodsFlowRow.community_entity_id == community_id, GoodsFlowRow.epoch >= ctx.epoch - 1, GoodsFlowRow.flow.in_(list(GOODS_SOURCES))
        )
    )
    by_epoch: dict[int, dict[CommodityKind, int]] = {}
    for row in rows:
        epoch = by_epoch.setdefault(row.epoch, {})
        epoch[row.commodity] = epoch.get(row.commodity, 0) + max(0, row.quantity)
    return by_epoch.get(ctx.epoch) or by_epoch.get(ctx.epoch - 1) or {}


async def tithe_base(ctx: TickContext, church: Church) -> list[EntityRow]:
    lands = {row.holding_entity_id for row in await holdings_of(ctx, church, HoldingKind.LAND)}
    return [member for member in church.members if member.id in lands]


async def tithe(ctx: TickContext, church: Church, laws: LawBook) -> int:
    doctrine = church.doctrine
    if doctrine is None:
        return 0
    table = ctx.rules.tithes
    ledger = goods_of(ctx.session, ctx.epoch)
    units = 0
    measured = False
    for member in await tithe_base(ctx, church):
        output = await output_of(ctx, member.id)
        if not output:
            continue
        measured = True
        rate, enforcement = await tithe_terms(ctx, church, laws, member.id)
        for commodity, made in sorted(output.items()):
            due = round_half_up(made * rate / PERCENT * enforcement / PERCENT)
            if due > 0:
                units += await ledger.take_units(member.id, commodity, due, GoodsFlow.OFFERING)
    if not measured:
        followers = stat(church.cult, "followers") or 0
        units = round_half_up(followers * table.output_per_100 / PERCENT * doctrine.tithe_rate / PERCENT * table.voluntary_pct / PERCENT)
    return credit(doctrine, round_half_up(units * table.unit_value_pct / PERCENT))


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
    table = ctx.rules.tithes
    eased = 0
    for member in church.members:
        pressures = await pressures_of(ctx.session, member.id)
        if pressures.get(PressureKind.POVERTY, 0) <= 0:
            continue
        pressures[PressureKind.POVERTY] = clamp_int(pressures[PressureKind.POVERTY] - table.alms_poverty, 0, PERCENT)
        await write_pressures(ctx.session, member.id, pressures)
        society = await ctx.session.get(CommunitySocietyRow, member.id)
        if society is not None:
            for social_class in POOR:
                key = f"satisfaction_{social_class.value}"
                setattr(society, key, clamp_int(getattr(society, key) + table.alms_satisfaction, 0, PERCENT))
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=member.id,
            subject_id=church.cult.id,
            kind=MemoryKind.FAMINE_AID,
            magnitude=table.alms_goodwill,
            epoch=ctx.epoch,
            note="fed by the alms of the faith",
        )
        eased += 1
    return eased


async def spend(ctx: TickContext, church: Church, knowledge: KnowledgeMap) -> str | None:
    doctrine = church.doctrine
    table = ctx.rules.tithes
    if doctrine is None:
        return None
    if church.holds(TenetKind.ASCETICISM) and affordable(doctrine, table.alms_cost):
        credit(doctrine, -table.alms_cost)
        return "alms" if await alms(ctx, church) else None
    if church.holds(TenetKind.MONASTIC_LEARNING) and affordable(doctrine, table.monastery_cost) and await build(ctx, church, HoldingKind.MONASTERY, knowledge):
        credit(doctrine, -table.monastery_cost)
        return "monastery"
    if affordable(doctrine, table.temple_cost) and await build(ctx, church, HoldingKind.TEMPLE, knowledge):
        credit(doctrine, -table.temple_cost)
        return "temple"
    if affordable(doctrine, table.alms_cost):
        credit(doctrine, -table.alms_cost)
        return "alms" if await alms(ctx, church) else None
    return None


async def saints(ctx: TickContext, church: Church, *, since: int | None = None) -> list[EntityRow]:
    homes = [member.id for member in church.members]
    if not homes:
        return []
    threshold = ctx.rules.doctrine.saint_threshold
    known = set(await ctx.session.scalars(select(RelicRow.saint_entity_id).where(RelicRow.saint_entity_id.is_not(None))))
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.DEAD,
        EntityRow.location_id.in_(homes),
        EntityRow.mortal_role.in_(list(CLERGY_SAINTS)),
    )
    statement = statement.where(EntityRow.end_epoch == ctx.epoch) if since is None else statement.where(EntityRow.end_epoch >= since)
    found = []
    for mortal in await ctx.session.scalars(statement.order_by(EntityRow.id)):
        piety = (await values_for(ctx.session, mortal.id)).get(ValueAxis.PIETY, 0)
        if mortal.id not in known and (piety >= threshold or (stat(mortal, "charisma") or 0) >= threshold):
            found.append(mortal)
    return found


async def bones_of(ctx: TickContext, church: Church, saint: EntityRow) -> EntityRow:
    bones = await create_record(
        ctx,
        RecordSpec(
            name=f"Bones of {saint.name}"[:200],
            entity_type=EntityType.ITEM,
            stats=ItemStats(),
            body=f"The bones of {saint.name}, kept by {church.cult.name} as a holy relic.",
            power=max(1, saint.power_level),
            world_id=saint.world_id,
            location_id=saint.location_id,
        ),
    )
    ctx.session.add(
        ItemProfileRow(
            item_entity_id=bones.id,
            item_class=ItemClass.HOLY_RELIC,
            material="bone",
            quality=PERCENT // 2,
            condition=PERCENT,
            reach=0,
            coverage=0,
            weight=0,
            curse=CurseKind.NONE,
            value=0,
            renown=clamp_int(saint.importance or 0, 0, PERCENT),
            symbol=True,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    await connect(ctx.session, church.cult.id, bones.id, BondKind.OWNS, ctx.epoch, description="the bones of its saint")
    return bones


async def canonise(ctx: TickContext, church: Church, saint: EntityRow, item: EntityRow | None = None) -> RelicRow:
    existing = await ctx.session.scalar(select(RelicRow).where(RelicRow.saint_entity_id == saint.id, RelicRow.cult_entity_id == church.cult.id).limit(1))
    if existing is not None and item is None:
        return existing
    relic = item or await bones_of(ctx, church, saint)
    row = await ctx.session.get(RelicRow, relic.id)
    if row is None:
        row = RelicRow(
            item_entity_id=relic.id,
            saint_entity_id=saint.id,
            cult_entity_id=church.cult.id,
            shrine_entity_id=saint.location_id,
            sanctity=PERCENT // 2,
            pilgrims=0,
            canonised_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(row)
    await hold(ctx, church, relic.id, HoldingKind.RELIC)
    await ctx.session.flush()
    return row


async def pilgrimage(ctx: TickContext, church: Church) -> tuple[int, int]:
    table = ctx.rules.tithes
    relics = list(await ctx.session.scalars(select(RelicRow).where(RelicRow.cult_entity_id == church.cult.id)))
    duty = table.pilgrimage_duty_pct if church.holds(TenetKind.PILGRIMAGE_DUTY) else PERCENT
    followers = stat(church.cult, "followers") or 0
    pilgrims = 0
    income = 0
    for relic in relics:
        if "pilgrims" not in relic.locked:
            relic.pilgrims = round_half_up(followers * relic.sanctity / PERCENT * table.pilgrims_per_follower_pct / PERCENT * duty / PERCENT)
        pilgrims += relic.pilgrims
        income += relic.pilgrims // table.pilgrims_per_income
    if church.doctrine is not None:
        credit(church.doctrine, income)
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
        chance = min(PERCENT, relic.pilgrims // ctx.rules.tithes.pilgrims_per_income)
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


async def devotion(ctx: TickContext, church: Church, patron_id: int | None) -> int:
    table = ctx.rules.doctrine
    if church.cult.engine_kind is EngineKind.RESURRECTION_ORDER:
        return 0
    followers = stat(church.cult, "followers") or 0
    zeal = stat(church.cult, "zeal") or 0
    gain = round_half_up(followers * table.devotion_per_1000 / THOUSAND * zeal / PERCENT)
    held = clamp_int((stat(church.cult, "devotion") or 0) + gain, 0, ctx.rules.death.devotion_cap)
    god = church.god
    if god is not None:
        tribute = round_half_up(held * table.devotion_tribute_pct / PERCENT)
        god.faith += tribute
        held -= tribute
    else:
        dead = await ctx.session.get(SonRow, patron_id) if patron_id is not None else None
        if dead is not None and not dead.alive and gain > 0:
            await add_devotion(ctx, dead, gain, church.cult)
    if church.doctrine is None or "devotion" not in church.doctrine.locked:
        set_stats(church.cult, devotion=held)
    return gain


def spend_devotion(church: Church, cost: int) -> bool:
    held = stat(church.cult, "devotion") or 0
    if held < cost:
        return False
    if church.doctrine is None or "devotion" not in church.doctrine.locked:
        set_stats(church.cult, devotion=held - cost)
    return True
