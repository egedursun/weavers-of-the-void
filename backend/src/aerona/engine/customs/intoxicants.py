from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.customs import KEEP_INTOXICATION_INTOXICANT_USES, KEEP_INTOXICATION_INTOXICANT_USES_2, PACKAGES
from aerona.catalog.life.mind import OPEN_STAGES
from aerona.catalog.life_traits import INTOXICANT_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.customs import IntoxicantCustomRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.tables.mind import GriefRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sacred import MysticRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.customs import Intoxicant, IntoxicantUse
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import IntoxicantTrait
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import stored_values
from aerona.engine.mortal.profile import is_held
from aerona.engine.primitives.folk import present_among, towns_of_people
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import StepDraft, record

HUNDRED = 100
DRINKS = having(INTOXICANT_TRAITS, IntoxicantTrait.DRINKS)


@dataclass
class IntoxicationTally:
    seeded: int = 0
    habits: int = 0
    brawls: int = 0
    visions: int = 0
    brewed: int = 0


async def customs_of(ctx: TickContext, people_id: int) -> list[IntoxicantCustomRow]:
    return list(
        await ctx.session.scalars(select(IntoxicantCustomRow).where(IntoxicantCustomRow.people_entity_id == people_id).order_by(IntoxicantCustomRow.intoxicant))
    )


async def seed_customs(ctx: TickContext, people: EntityRow, tally: IntoxicationTally) -> list[IntoxicantCustomRow]:
    found = await customs_of(ctx, people.id)
    if found:
        return found
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    rng = ctx.rng(seed_of("intoxicants", people.id))
    leisure, piety = values.get(ValueAxis.LEISURE, 0), values.get(ValueAxis.PIETY, 0)
    for intoxicant in rng.sample(list(Intoxicant), min(len(Intoxicant), ctx.rules.intoxication.customs_per_people)):
        use = IntoxicantUse.RITE if piety > leisure and rng.chance(50) else IntoxicantUse.DAILY if leisure > 0 and rng.chance(50) else IntoxicantUse.FEAST
        row = IntoxicantCustomRow(people_entity_id=people.id, intoxicant=intoxicant, use=use, acceptance=max(0, min(PERCENT, 50 + leisure // 2)), locked=[])
        ctx.session.add(row)
        found.append(row)
    tally.seeded += 1
    return found


async def habits(ctx: TickContext, people: EntityRow, row: IntoxicantCustomRow, tally: IntoxicationTally) -> None:
    table = ctx.rules.intoxication
    folk = await ctx.session.scalars(
        select(EntityRow)
        .where(await present_among(ctx.session, [people.id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    forbidden = row.use is IntoxicantUse.FORBIDDEN
    chance = table.habit_chance * row.acceptance / PERCENT * (table.forbidden_pct / PERCENT if forbidden else 1)
    for mortal in list(folk):
        if held(mortal.id) or not ctx.rng(seed_of("habit", mortal.id, row.intoxicant.value, ctx.epoch)).chance(chance):
            continue
        if await afflict(ctx, mortal, PACKAGES[row.intoxicant], Transmission.INGESTION) is None:
            continue
        tally.habits += 1
        profile = await ctx.session.get(MortalProfileRow, mortal.id)
        if forbidden and profile is not None and not is_held(profile, "infamy"):
            profile.infamy = clamp_int(profile.infamy + table.forbidden_infamy, 0, PERCENT)


async def mourn(ctx: TickContext, people: EntityRow) -> None:
    mourners = await ctx.session.scalars(
        select(GriefRow.mourner_node_id)
        .join(EntityRow, EntityRow.id == GriefRow.mourner_node_id)
        .where(await present_among(ctx.session, [people.id]), GriefRow.stage.in_(list(OPEN_STAGES)))
    )
    for mourner in sorted(set(mourners)):
        profile = await ctx.session.get(MortalProfileRow, mourner)
        if profile is not None and not held(mourner) and not is_held(profile, "stress"):
            profile.stress = clamp_int(profile.stress - ctx.rules.intoxication.mourning_calm, 0, PERCENT)


async def cheer(ctx: TickContext, town: EntityRow, amount: int) -> None:
    society = await ctx.session.get(CommunitySocietyRow, town.id)
    if society is None or amount <= 0:
        return
    for social_class in SocialClass:
        key = f"satisfaction_{social_class.value}"
        setattr(society, key, clamp_int(int(getattr(society, key)) + amount, 0, PERCENT))


async def brawls(ctx: TickContext, people: EntityRow, tally: IntoxicationTally) -> None:
    towns = await towns_of_people(ctx.session, people.id)
    if not towns:
        return
    for gathering in list(
        await ctx.session.scalars(
            select(GatheringRow).where(GatheringRow.epoch == ctx.epoch, GatheringRow.place_entity_id.in_(towns)).order_by(GatheringRow.id)
        )
    ):
        if not ctx.rng(seed_of("brawl", gathering.id)).chance(ctx.rules.intoxication.brawl_chance):
            continue
        guests = list(
            await ctx.session.scalars(
                select(GatheringGuestRow.node_id).where(GatheringGuestRow.gathering_id == gathering.id, GatheringGuestRow.attended.is_(True))
            )
        )
        hurt = await ctx.session.get(EntityRow, ctx.rng(seed_of("brawl.hurt", gathering.id)).pick(guests)) if guests else None
        if hurt is None or held(hurt.id) or hurt.entity_type is not EntityType.MORTAL:
            continue
        await apply_hits(
            ctx, hurt, Harm(damage=ctx.rules.intoxication.brawl_damage, cause=HarmCause.ACCIDENT, death_cause="died of a brawl at a gathering"), lethal=False
        )
        tally.brawls += 1
        await record(
            ctx,
            "intoxication.brawl",
            roles={IncidentRole.VICTIM: hurt.id, IncidentRole.HOST: gathering.host_node_id, IncidentRole.GUEST: guests},
            facts={"damage": ctx.rules.intoxication.brawl_damage},
            steps=(
                StepDraft(StepAction.QUARREL, target=hurt.id),
                StepDraft(StepAction.STRIKE, target=hurt.id, amount=ctx.rules.intoxication.brawl_damage, unit=FactUnit.HP),
            ),
            place=gathering.place_entity_id,
        )


async def visions(ctx: TickContext, people: EntityRow, tally: IntoxicationTally) -> None:
    seekers = await ctx.session.scalars(
        select(MysticRow)
        .join(EntityRow, EntityRow.id == MysticRow.mortal_entity_id)
        .where(await present_among(ctx.session, [people.id]), EntityRow.status == EntityStatus.CANON)
    )
    for mystic in list(seekers):
        if held(mystic.mortal_entity_id) or not ctx.rng(seed_of("vision.intoxicant", mystic.mortal_entity_id, ctx.epoch)).chance(
            ctx.rules.intoxication.vision_chance
        ):
            continue
        if "visions" not in mystic.locked:
            mystic.visions += 1
        mystic.last_vision_epoch = ctx.epoch
        tally.visions += 1


async def brew(ctx: TickContext, people: EntityRow, tally: IntoxicationTally) -> None:
    for town in list(
        await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(await towns_of_people(ctx.session, people.id))).order_by(EntityRow.id))
    ):
        if held(town.id):
            continue
        want = round_half_up(stat_or(town, "population", 0) / HUNDRED * ctx.rules.intoxication.brew_per_100)
        taken = await goods_of(ctx.session, ctx.epoch).take_units(town.id, CommodityKind.BREW_BASE, want, GoodsFlow.CONSUMPTION)
        tally.brewed += taken
        if taken and want:
            await cheer(ctx, town, ctx.rules.intoxication.brew_cheer * taken // want)


async def keep_intoxication(ctx: TickContext, tally: IntoxicationTally) -> None:
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(people.id):
            continue
        rows = await seed_customs(ctx, people, tally)
        uses = {row.use for row in rows}
        for row in rows:
            if row.use in KEEP_INTOXICATION_INTOXICANT_USES_2:
                await habits(ctx, people, row, tally)
        if IntoxicantUse.MOURNING in uses:
            await mourn(ctx, people)
        if IntoxicantUse.FEAST in uses and any(row.intoxicant in DRINKS for row in rows):
            await brawls(ctx, people, tally)
        if IntoxicantUse.RITE in uses:
            await visions(ctx, people, tally)
        if uses & KEEP_INTOXICATION_INTOXICANT_USES:
            await brew(ctx, people, tally)
    await ctx.session.flush()
