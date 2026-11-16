from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.culture import ProphecyConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import HolyOrderProfileRow
from aerona.db.tables.faith import CultDoctrineRow, CultOfficeRow, CultTenetRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sacred import FaithClimateRow, MillenarianRow, MysticRow, TheodicyCrisisRow, VisionRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import CollectiveActKind, CollectiveTrigger
from aerona.domain.enums.culture import ProphecyState, Technique
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.mind import ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.sacred import MillenarianStage, MysticState, TheodicyCause, TheodicyResolution, VisionKind
from aerona.domain.enums.society import Commodity
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.body.conditions import gain_condition
from aerona.engine.collective.crowds import begin_movement
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import psi_of
from aerona.engine.divine.standing import standing_row
from aerona.engine.faith.zealotry import record_heresy
from aerona.engine.loops.delay import lagged
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.thoughts import think
from aerona.engine.notes import note
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.sacred.places import church_of, plagued_regions, realm_of_town, region_of, town_of
from aerona.engine.sacred.signs import defeated_realms, miracles_by_region, omen_worlds, struck_regions

MIDDLING = 50
TEN = 10
THOUSAND = 1000
CONVICTION_STEP = 5
LIVING_MOVEMENT = (MillenarianStage.STIRRING, MillenarianStage.GATHERING, MillenarianStage.VIGIL, MillenarianStage.MARCHING, MillenarianStage.REDATED)
HERESY = "heresy"
SECT = "sect"


@dataclass
class MysteryTally:
    mystics: int = 0
    visions: int = 0
    genuine: int = 0
    founded: int = 0
    persecuted: int = 0
    movements: int = 0
    vigils: int = 0
    attacks: int = 0
    redated: int = 0
    sects: int = 0
    dispersed: int = 0
    crises: int = 0
    answered: int = 0
    argued: int = 0
    doctrines: int = 0
    conversions: int = 0
    drifts: int = 0


async def patron_of(ctx: TickContext, entity_id: int) -> int | None:
    book = await ctx.divine()
    gods, _ = await book.faithful_of(ctx.session, entity_id)
    return min(gods) if gods else None


async def see_vision(ctx: TickContext, row: MysticRow, mortal: EntityRow, sender: int | None, tally: MysteryTally) -> VisionRow:
    table = ctx.rules.mysticism
    vision = VisionRow(
        mystic_entity_id=row.mortal_entity_id,
        epoch=ctx.epoch,
        kind=ctx.rng(f"vision.kind.{mortal.id}").pick(list(VisionKind)),
        sender_node_id=sender,
        genuine=sender is not None,
        awe=table.awe,
        locked=[],
    )
    ctx.session.add(vision)
    if "visions" not in row.locked:
        row.visions += 1
    if sender is not None:
        row.genuine_visions += 1
        row.answered_by_node_id = sender
        tally.genuine += 1
    if "followers" not in row.locked:
        row.followers += round_half_up(table.followers_per_vision * stat_or(mortal, "charisma", MIDDLING) / MIDDLING)
    row.last_vision_epoch = ctx.epoch
    tally.visions += 1
    await gain_condition(ctx, mortal, ConditionKind.VISIONS, HarmCause.GOD if sender is not None else HarmCause.RITUAL, source_node_id=sender, announce=False)
    await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.TOUCHED_BY_A_GOD, ctx.epoch, subject_id=sender)
    await ctx.session.flush()
    return vision


async def become_mystic(ctx: TickContext, mortal: EntityRow, sender: int | None, tally: MysteryTally) -> MysticRow:
    town = await town_of(ctx.session, mortal)
    cult = await church_of(ctx.session, town) if town is not None else None
    row = MysticRow(
        mortal_entity_id=mortal.id, state=MysticState.SEEKER, cult_entity_id=cult.id if cult is not None else None, since_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.mystics += 1
    await see_vision(ctx, row, mortal, sender, tally)
    await note(ctx, f"{mortal.name} was seized by a vision.", key="sacred.mystic", ids=[mortal.id])
    return row


async def open_to_visions(ctx: TickContext, mortal: EntityRow) -> bool:
    table = ctx.rules.mysticism
    if stat_or(mortal, "wisdom", 0) < table.wisdom_floor:
        return False
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    return values.get(ValueAxis.PIETY, 0) >= table.piety_floor


async def contemplative(ctx: TickContext, mortal: EntityRow) -> bool:
    town = await town_of(ctx.session, mortal)
    if town is None:
        return False
    if await has_technique(ctx.session, town.id, Technique.MONASTICISM):
        return True
    cult = await church_of(ctx.session, town)
    tenet = (
        await ctx.session.scalar(
            select(CultTenetRow.cult_entity_id).where(CultTenetRow.cult_entity_id == cult.id, CultTenetRow.tenet == TenetKind.MONASTIC_LEARNING).limit(1)
        )
        if cult is not None
        else None
    )
    return tenet is not None


async def answering_god(ctx: TickContext, mortal: EntityRow, key: str) -> int | None:
    god = await patron_of(ctx, mortal.id)
    if god is None or held(god) or not ctx.rng(key).chance(ctx.rules.mysticism.answer_chance):
        return None
    return god


async def seize_new(ctx: TickContext, tally: MysteryTally) -> None:
    table = ctx.rules.mysticism
    known = select(MysticRow.mortal_entity_id)
    mortals = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(known))
        .order_by(EntityRow.id)
    )
    for mortal in list(mortals):
        if tally.mystics >= table.mystics_per_epoch:
            return
        if held(mortal.id) or stat_or(mortal, "wisdom", 0) < table.wisdom_floor:
            continue
        chance = table.vision_chance * (1 + table.contemplative_pct / PERCENT if await contemplative(ctx, mortal) else 1)
        if not ctx.rng(f"mystic.{mortal.id}").chance(chance) or not await open_to_visions(ctx, mortal):
            continue
        await become_mystic(ctx, mortal, await answering_god(ctx, mortal, f"mystic.answer.{mortal.id}"), tally)


async def found_heresy(ctx: TickContext, row: MysticRow, mortal: EntityRow, town: EntityRow) -> EntityRow:
    sect = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.CULT,
            name=f"Followers of {mortal.name}",
            body=f"Those who believe the visions of {mortal.name} gathered apart from the church.",
            stats=CultStats(followers=max(1, row.followers), zeal=clamp_int(row.persecution + MIDDLING, 0, PERCENT), influence=row.reverence),
            power=max(1, mortal.power_level),
            location_id=town.id,
            world_id=town.world_id,
            subtype=HERESY,
        ),
    )
    if row.cult_entity_id is not None and await living_entity(ctx.session, row.cult_entity_id) is not None:
        await record_heresy(ctx, sect, row.cult_entity_id)
    god = row.answered_by_node_id or await patron_of(ctx, mortal.id)
    if god is not None:
        await connect(ctx.session, sect.id, god, BondKind.WORSHIPS, ctx.epoch, description=f"the visions of {mortal.name}")
    await connect(ctx.session, mortal.id, sect.id, BondKind.MEMBER_OF, ctx.epoch, description="its founder")
    return sect


async def found_order(ctx: TickContext, row: MysticRow, mortal: EntityRow, town: EntityRow) -> EntityRow:
    order = await found_faction(ctx, town, FactionKind.HOLY_ORDER)
    if await ctx.session.get(HolyOrderProfileRow, order.id) is None:
        ctx.session.add(HolyOrderProfileRow(faction_entity_id=order.id, cult_entity_id=row.cult_entity_id, locked=[]))
    await connect(ctx.session, mortal.id, order.id, BondKind.MEMBER_OF, ctx.epoch, description="its founder")
    return order


async def judge_mystic(ctx: TickContext, row: MysticRow, mortal: EntityRow, tally: MysteryTally) -> None:
    table = ctx.rules.mysticism
    doctrine = await ctx.session.get(CultDoctrineRow, row.cult_entity_id) if row.cult_entity_id is not None else None
    clergy = await ctx.session.scalar(select(CultOfficeRow.id).where(CultOfficeRow.holder_entity_id == mortal.id).limit(1))
    if doctrine is not None and clergy is None and doctrine.orthodoxy >= table.orthodoxy_persecutes:
        if "persecution" not in row.locked:
            row.persecution = clamp_int(row.persecution + table.persecution_step, 0, PERCENT)
    elif "reverence" not in row.locked:
        row.reverence = clamp_int(row.reverence + table.persecution_step, 0, PERCENT)
    persecuted = row.persecution >= table.persecuted_at and row.persecution >= row.reverence
    if persecuted:
        tally.persecuted += 1
        profile = await ctx.session.get(MortalProfileRow, mortal.id)
        if profile is not None and "stress" not in profile.locked:
            profile.stress += table.persecution_stress
    if "state" in row.locked or row.state is MysticState.FOUNDER:
        return
    if row.last_vision_epoch is not None and ctx.epoch - row.last_vision_epoch >= table.lapse_epochs:
        row.state = MysticState.LAPSED
        return
    if persecuted:
        row.state = MysticState.PERSECUTED
    elif row.reverence >= table.revered_at:
        row.state = MysticState.REVERED
    elif row.visions >= table.visionary_at:
        row.state = MysticState.VISIONARY
    town = await town_of(ctx.session, mortal)
    if row.followers >= table.found_at and row.founded_entity_id is None and town is not None and not held(town.id):
        founded = await found_heresy(ctx, row, mortal, town) if row.state is MysticState.PERSECUTED else await found_order(ctx, row, mortal, town)
        row.founded_entity_id = founded.id
        row.state = MysticState.FOUNDER
        tally.founded += 1
        await note(ctx, f"{mortal.name} founded {founded.name} on the strength of visions.", key="sacred.mystic_founded", ids=[mortal.id, founded.id])


async def keep_mystics(ctx: TickContext, tally: MysteryTally) -> None:
    table = ctx.rules.mysticism
    await seize_new(ctx, tally)
    for row in list(await ctx.session.scalars(select(MysticRow).order_by(MysticRow.mortal_entity_id))):
        mortal = await living_entity(ctx.session, row.mortal_entity_id)
        if mortal is None or held(mortal.id):
            continue
        if row.last_vision_epoch != ctx.epoch and row.state is not MysticState.LAPSED and ctx.rng(f"vision.again.{mortal.id}").chance(table.again_chance):
            await see_vision(ctx, row, mortal, await answering_god(ctx, mortal, f"vision.answer.{mortal.id}"), tally)
        await judge_mystic(ctx, row, mortal, tally)


async def end_prophecy(ctx: TickContext, town: EntityRow) -> ProphecyConditionRow | None:
    rows = await ctx.session.scalars(
        select(ProphecyConditionRow)
        .join(EntityRow, EntityRow.id == ProphecyConditionRow.prophecy_entity_id)
        .where(ProphecyConditionRow.state == ProphecyState.PENDING, EntityRow.world_id == town.world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(ProphecyConditionRow.prophecy_entity_id)
    )
    return next(iter(rows), None)


async def pressure_on(ctx: TickContext, town: EntityRow, omens: set[int]) -> tuple[int, ProphecyConditionRow | None]:
    table = ctx.rules.millenarianism
    prophecy = await end_prophecy(ctx, town)
    pressure = (1 if await psi_of(ctx.session, town.id) >= table.psi_floor else 0) + (1 if town.world_id in omens else 0)
    cosmos = await CosmosRepository(ctx.session).get()
    storyteller = await ctx.session.get(StorytellerRow, town.world_id) if town.world_id is not None else None
    pressure += 1 if cosmos is not None and cosmos.doom_clock >= table.doom_at else 0
    pressure += 1 if storyteller is not None and storyteller.tension >= table.tension_at else 0
    return pressure + (1 if prophecy is not None else 0), prophecy


async def begin_millenarian(ctx: TickContext, town: EntityRow, *, prophet_id: int | None, prophecy: ProphecyConditionRow | None) -> MillenarianRow:
    table = ctx.rules.millenarianism
    members = round_half_up(stat_or(town, "population", 0) * table.gather_pct / PERCENT)
    movement = await begin_movement(ctx, town, CollectiveActKind.REVIVAL, CollectiveTrigger.OMEN, members=members, share=table.gather_pct)
    cult = await church_of(ctx.session, town)
    end = ctx.epoch + table.horizon
    if prophecy is not None and prophecy.deadline_epoch is not None and prophecy.deadline_epoch > ctx.epoch:
        end = min(end, prophecy.deadline_epoch)
    row = MillenarianRow(
        settlement_entity_id=town.id,
        cult_entity_id=cult.id if cult is not None else None,
        prophet_entity_id=prophet_id if prophet_id is not None else movement.leader_entity_id,
        prophecy_entity_id=prophecy.prophecy_entity_id if prophecy is not None else None,
        movement_id=movement.id,
        stage=MillenarianStage.STIRRING,
        end_epoch=end,
        members=members,
        conviction=MIDDLING + CONVICTION_STEP * TEN // 2,
        dates_set=1,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"The faithful of {town.name} began to await the end, set for epoch {end}.", key="sacred.millenarian", ids=[town.id])
    return row


async def stir_towns(ctx: TickContext, tally: MysteryTally) -> None:
    table = ctx.rules.millenarianism
    busy = select(MillenarianRow.settlement_entity_id).where(MillenarianRow.stage.in_(LIVING_MOVEMENT))
    omens = await omen_worlds(ctx)
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(busy))
        .order_by(EntityRow.id)
    )
    for town in list(towns):
        if tally.movements >= table.movements_per_epoch:
            return
        if held(town.id):
            continue
        pressure, prophecy = await pressure_on(ctx, town, omens)
        if pressure and ctx.rng(f"millenarian.{town.id}").chance(table.stir_chance * pressure):
            await begin_millenarian(ctx, town, prophet_id=None, prophecy=prophecy)
            tally.movements += 1


async def found_sect(ctx: TickContext, row: MillenarianRow, town: EntityRow) -> EntityRow:
    sect = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.CULT,
            name=f"Watchers of {town.name}",
            body=f"Those who kept awaiting the end in {town.name} held together after the day passed.",
            stats=CultStats(followers=max(1, row.members), zeal=row.conviction, influence=0),
            power=max(1, town.power_level),
            location_id=town.id,
            world_id=town.world_id,
            subtype=SECT,
        ),
    )
    if row.cult_entity_id is not None and await living_entity(ctx.session, row.cult_entity_id) is not None:
        await record_heresy(ctx, sect, row.cult_entity_id)
    god = await patron_of(ctx, town.id)
    if god is not None:
        await connect(ctx.session, sect.id, god, BondKind.WORSHIPS, ctx.epoch, description="the end awaited")
    return sect


async def disappoint(ctx: TickContext, row: MillenarianRow, town: EntityRow, tally: MysteryTally) -> None:
    table = ctx.rules.millenarianism
    row.conviction = max(0, row.conviction - table.conviction_loss)
    redate = max(0, table.redate_chance - (row.dates_set - 1) * table.redate_decay)
    if ctx.rng(f"millenarian.redate.{row.id}.{row.dates_set}").chance(redate):
        row.stage = MillenarianStage.REDATED
        row.end_epoch = ctx.epoch + table.horizon
        row.dates_set += 1
        tally.redated += 1
        await note(
            ctx, f"The day passed in {town.name}; its faithful read the prophecy anew and set epoch {row.end_epoch}.", key="sacred.redated", ids=[town.id]
        )
        return
    if ctx.rng(f"millenarian.sect.{row.id}").chance(table.sect_chance):
        sect = await found_sect(ctx, row, town)
        row.sect_entity_id = sect.id
        row.stage = MillenarianStage.SECT
        tally.sects += 1
    else:
        row.stage = MillenarianStage.DISPERSED
        tally.dispersed += 1
    row.ended_epoch = ctx.epoch
    row.idle_share = 0


async def keep_vigil(ctx: TickContext, row: MillenarianRow, town: EntityRow, tally: MysteryTally) -> None:
    table = ctx.rules.millenarianism
    row.stage = MillenarianStage.VIGIL
    tally.vigils += 1
    wealth = stat_or(town, "wealth", 0)
    given = round_half_up(wealth * table.give_up_pct / PERCENT)
    if given:
        set_stats(town, wealth=max(0, wealth - given))
        row.given_up += given
    if "idle_share" not in row.locked:
        row.idle_share = table.idle_pct
    lost = row.idle_share // TEN * table.idle_food
    food = await stock(ctx.session, ctx.rules, town.id, Commodity.FOOD)
    if lost and food:
        await shift_stock(ctx.session, ctx.rules, town.id, Commodity.FOOD, -min(lost, food), epoch=ctx.epoch, flow=GoodsFlow.LOSS)
    if row.conviction >= table.march_at:
        row.stage = MillenarianStage.MARCHING
        people = stat_or(town, "population", 0)
        killed = round_half_up(people * table.attack_per_mille / THOUSAND)
        if killed:
            set_stats(town, population=max(0, people - killed))
        row.attacks += 1
        tally.attacks += 1


async def advance_movement(ctx: TickContext, row: MillenarianRow, tally: MysteryTally) -> None:
    table = ctx.rules.millenarianism
    town = await living_entity(ctx.session, row.settlement_entity_id)
    if town is None or held(town.id) or "stage" in row.locked:
        return
    prophecy = await ctx.session.get(ProphecyConditionRow, row.prophecy_entity_id) if row.prophecy_entity_id is not None else None
    if prophecy is not None and prophecy.state is ProphecyState.FULFILLED:
        row.stage = MillenarianStage.SECT
        row.ended_epoch = ctx.epoch
        row.sect_entity_id = (await found_sect(ctx, row, town)).id
        tally.sects += 1
        return
    if ctx.epoch >= row.end_epoch:
        await disappoint(ctx, row, town, tally)
        return
    if row.stage in {MillenarianStage.STIRRING, MillenarianStage.REDATED}:
        row.stage = MillenarianStage.GATHERING
    if "members" not in row.locked:
        row.members = min(stat_or(town, "population", 0), row.members + round_half_up(row.members * table.recruit_pct / PERCENT))
    if "conviction" not in row.locked:
        row.conviction = clamp_int(row.conviction + CONVICTION_STEP, 0, PERCENT)
    if row.end_epoch - ctx.epoch <= table.vigil_epochs:
        await keep_vigil(ctx, row, town, tally)


async def keep_millenarians(ctx: TickContext, tally: MysteryTally) -> None:
    await stir_towns(ctx, tally)
    rows = await ctx.session.scalars(
        select(MillenarianRow).where(MillenarianRow.stage.in_(LIVING_MOVEMENT), MillenarianRow.since_epoch < ctx.epoch).order_by(MillenarianRow.id)
    )
    for row in list(rows):
        await advance_movement(ctx, row, tally)


async def suffering_of(ctx: TickContext, town: EntityRow, signs: tuple[set[int], set[int], set[int]]) -> tuple[int, TheodicyCause | None]:
    table = ctx.rules.theodicy
    plagued, struck, defeated = signs
    region = await region_of(ctx.session, town)
    found: list[tuple[int, TheodicyCause]] = []
    if region is not None and region.id in plagued:
        found.append((table.plague_suffering, TheodicyCause.PLAGUE))
    if await stock(ctx.session, ctx.rules, town.id, Commodity.FOOD) <= 0:
        found.append((table.famine_suffering, TheodicyCause.FAMINE))
    realm = await realm_of_town(ctx.session, town.id)
    if realm is not None and realm in defeated:
        found.append((table.defeat_suffering, TheodicyCause.DEFEAT))
    if region is not None and region.id in struck:
        found.append((table.disaster_suffering, TheodicyCause.DISASTER))
    if not found:
        return 0, None
    worst = max(found, key=lambda item: (item[0], item[1].value))
    return clamp_int(sum(item[0] for item in found), 0, PERCENT), worst[1]


async def open_crisis(ctx: TickContext, town: EntityRow, cult: EntityRow, cause: TheodicyCause, suffering: int) -> TheodicyCrisisRow:
    row = TheodicyCrisisRow(
        cult_entity_id=cult.id,
        community_entity_id=town.id,
        god_node_id=await patron_of(ctx, cult.id),
        cause=cause,
        suffering=suffering,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"Suffering in {town.name} put the teaching of {cult.name} to the test.", key="sacred.theodicy", ids=[town.id, cult.id])
    return row


async def test_doctrines(ctx: TickContext, tally: MysteryTally) -> None:
    table = ctx.rules.theodicy
    signs = (await plagued_regions(ctx.session), await struck_regions(ctx), await defeated_realms(ctx))
    open_towns = select(TheodicyCrisisRow.community_entity_id).where(TheodicyCrisisRow.resolution == TheodicyResolution.PENDING)
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(open_towns))
        .order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        suffering, cause = await suffering_of(ctx, town, signs)
        suffering = await lagged(ctx, BalanceLoop.THEODICY, town.id, suffering)
        if cause is None or suffering < table.suffering_at:
            continue
        cult = await church_of(ctx.session, town)
        if cult is None or held(cult.id):
            continue
        await open_crisis(ctx, town, cult, cause, suffering)
        tally.crises += 1


async def theologian_of(ctx: TickContext, cult_id: int) -> EntityRow | None:
    holders = await ctx.session.scalars(
        select(CultOfficeRow.holder_entity_id).where(CultOfficeRow.cult_entity_id == cult_id, CultOfficeRow.holder_entity_id.is_not(None))
    )
    found = [await living_entity(ctx.session, item) for item in holders]
    living = [item for item in found if item is not None]
    return max(living, key=lambda item: (stat_or(item, "intellect", 0), -item.id), default=None)


async def seek_another_way(ctx: TickContext, row: TheodicyCrisisRow, town: EntityRow, cult: EntityRow, tally: MysteryTally) -> TheodicyResolution:
    table = ctx.rules.theodicy
    rng = ctx.rng(f"theodicy.way.{row.id}")
    theologian = await theologian_of(ctx, cult.id)
    row.theologian_entity_id = theologian.id if theologian is not None else None
    argue = table.argue_base + (stat_or(theologian, "intellect", 0) // 2 if theologian is not None else 0)
    if rng.chance(argue):
        outcome = TheodicyResolution.ARGUED
        tally.argued += 1
    elif rng.chance(table.doctrine_chance):
        outcome = TheodicyResolution.NEW_DOCTRINE
        climate = await ctx.session.get(FaithClimateRow, town.id)
        silent = climate is not None and climate.silent_epochs >= table.silent_hidden
        trial = await ctx.session.get(CultTenetRow, (cult.id, TenetKind.SACRED_SUFFERING))
        tenet = TenetKind.HIDDEN_GOD if silent or trial is not None else TenetKind.SACRED_SUFFERING
        if await ctx.session.get(CultTenetRow, (cult.id, tenet)) is None:
            ctx.session.add(CultTenetRow(cult_entity_id=cult.id, tenet=tenet, since_epoch=ctx.epoch))
        tally.doctrines += 1
    elif rng.chance(table.conversion_chance) and row.god_node_id is not None:
        outcome = TheodicyResolution.CONVERSION
        standing = await standing_row(ctx, town.id, row.god_node_id)
        if "neglect" not in standing.locked:
            standing.neglect = clamp_int(standing.neglect + table.conversion_neglect, 0, PERCENT)
        tally.conversions += 1
    else:
        outcome = TheodicyResolution.SECULAR_DRIFT
        set_stats(town, piety=max(0, stat_or(town, "piety", 0) - table.drift_piety))
        tally.drifts += 1
    return outcome


async def resolve_crisis(ctx: TickContext, row: TheodicyCrisisRow, miracles: dict[int, set[int]], tally: MysteryTally) -> None:
    table = ctx.rules.theodicy
    town = await living_entity(ctx.session, row.community_entity_id)
    cult = await living_entity(ctx.session, row.cult_entity_id)
    if town is None or cult is None or held(town.id) or "resolution" in row.locked:
        return
    region = await region_of(ctx.session, town)
    if row.god_node_id is not None and region is not None and row.god_node_id in miracles.get(region.id, set()):
        row.answered = True
    if row.answered:
        outcome = TheodicyResolution.ANSWERED
        if row.god_node_id is not None:
            standing = await standing_row(ctx, town.id, row.god_node_id)
            if "love" not in standing.locked:
                standing.love = clamp_int(standing.love + table.answer_love, 0, PERCENT)
        tally.answered += 1
    elif ctx.epoch - row.started_epoch < table.window:
        return
    else:
        outcome = await seek_another_way(ctx, row, town, cult, tally)
    row.resolution = outcome
    row.resolved_epoch = ctx.epoch
    await note(ctx, f"The crisis of faith in {town.name} ended: {outcome.value.replace('_', ' ')}.", key="sacred.theodicy_resolved", ids=[town.id, cult.id])


async def keep_theodicy(ctx: TickContext, tally: MysteryTally) -> None:
    await test_doctrines(ctx, tally)
    rows = await ctx.session.scalars(select(TheodicyCrisisRow).where(TheodicyCrisisRow.resolution == TheodicyResolution.PENDING).order_by(TheodicyCrisisRow.id))
    pending = list(rows)
    if not pending:
        return
    miracles = await miracles_by_region(ctx, min(row.started_epoch for row in pending))
    for row in pending:
        await resolve_crisis(ctx, row, miracles, tally)


async def keep_mysteries(ctx: TickContext, tally: MysteryTally) -> None:
    await keep_mystics(ctx, tally)
    await keep_millenarians(ctx, tally)
    await keep_theodicy(ctx, tally)
    await ctx.session.flush()
