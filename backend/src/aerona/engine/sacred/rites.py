from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.sacred import SACRAMENT_GUARDS, STATE_MODELS, STRATUM_MODELS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.discovery import TheoryProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, CultDoctrineRow, CultTenetRow, ReincarnationRow, SoulJudgementRow, SpiritProfileRow
from aerona.db.tables.mind import DreamRow
from aerona.db.tables.sacred import DoctrineAfterlifeRow, DoctrineSacramentRow, FaithClimateRow, SacramentRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.faith import AfterlifeState, JudgementDoctrine, TenetKind
from aerona.domain.enums.mind import DreamKind
from aerona.domain.enums.sacred import AfterlifeModel, SacramentKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import tech_factor
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag, has_flag, living_entity, remove_flag
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.sacred.guards import perform
from aerona.engine.sacred.mysteries import patron_of
from aerona.engine.sacred.places import church_of, plagued_regions, realm_of_town, region_of, town_of
from aerona.engine.sacred.signs import dominion_over, miracles_by_region, struck_regions
from aerona.engine.services.war import ongoing_wars

MIDDLE = 50
CITY_CAP = 20
MODEL_BY_TENET = (
    (TenetKind.REINCARNATION, AfterlifeModel.REBIRTH),
    (TenetKind.VOID_COMMUNION, AfterlifeModel.UNION),
    (TenetKind.ANCESTOR_VENERATION, AfterlifeModel.ANCESTOR_HALL),
    (TenetKind.HOLY_WAR, AfterlifeModel.WARRIOR_HALL),
    (TenetKind.MARTYRDOM_GLORY, AfterlifeModel.WARRIOR_HALL),
    (TenetKind.SOULS_REST, AfterlifeModel.COMMON_REALM),
)


@dataclass
class RiteTally:
    taught: int = 0
    performed: int = 0
    missed: int = 0
    afterlives: int = 0
    shocks: int = 0
    testimonies: int = 0
    drifted: int = 0
    godless: int = 0
    faithful: int = 0


async def churches(ctx: TickContext) -> list[int]:
    return list(
        await ctx.session.scalars(
            select(CultDoctrineRow.cult_entity_id)
            .join(EntityRow, EntityRow.id == CultDoctrineRow.cult_entity_id)
            .where(EntityRow.status == EntityStatus.CANON)
            .order_by(CultDoctrineRow.cult_entity_id)
        )
    )


async def teach_sacraments(ctx: TickContext, cult_id: int, tally: RiteTally) -> None:
    taught = set(await ctx.session.scalars(select(DoctrineSacramentRow.kind).where(DoctrineSacramentRow.cult_entity_id == cult_id)))
    if taught:
        return
    for kind in SacramentKind:
        ctx.session.add(
            DoctrineSacramentRow(
                cult_entity_id=cult_id, kind=kind, protection=SACRAMENT_GUARDS[kind], strength=ctx.rules.sacraments.strength, since_epoch=ctx.epoch, locked=[]
            )
        )
        tally.taught += 1


async def due_rites(ctx: TickContext) -> list[tuple[EntityRow, SacramentKind]]:
    table = ctx.rules.sacraments
    mortals = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    found: list[tuple[EntityRow, SacramentKind]] = [
        (row, SacramentKind.BIRTH_BLESSING) for row in await ctx.session.scalars(mortals.where(EntityRow.birth_epoch == ctx.epoch).order_by(EntityRow.id))
    ]
    wed = select(BondRow.source_node_id).where(BondRow.kind == BondKind.SPOUSE_OF, BondRow.epoch == ctx.epoch)
    married = select(SacramentRow.mortal_entity_id).where(SacramentRow.kind == SacramentKind.MARRIAGE, SacramentRow.epoch == ctx.epoch)
    found.extend(
        (row, SacramentKind.MARRIAGE)
        for row in await ctx.session.scalars(mortals.where(EntityRow.id.in_(wed), EntityRow.id.not_in(married)).order_by(EntityRow.id))
    )
    initiated = select(SacramentRow.mortal_entity_id).where(SacramentRow.kind == SacramentKind.INITIATION)
    for row in await ctx.session.scalars(mortals.where(EntityRow.id.not_in(initiated), EntityRow.birth_epoch < ctx.epoch).order_by(EntityRow.id)):
        if stat_or(row, "age", 0) >= table.initiation_age:
            found.append((row, SacramentKind.INITIATION))
    return found


async def keep_sacraments(ctx: TickContext, tally: RiteTally) -> None:
    for cult_id in await churches(ctx):
        if not held(cult_id):
            await teach_sacraments(ctx, cult_id, tally)
    await ctx.session.flush()
    plagued = await plagued_regions(ctx.session)
    for mortal, kind in await due_rites(ctx):
        if tally.performed + tally.missed >= ctx.rules.sacraments.rites_per_epoch:
            return
        if held(mortal.id):
            continue
        row = await perform(ctx, mortal, kind, plagued)
        if row is None:
            continue
        if row.missed:
            tally.missed += 1
        else:
            tally.performed += 1


async def taught_model(ctx: TickContext, cult_id: int) -> AfterlifeModel:
    tenets = set(await ctx.session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == cult_id)))
    for tenet, model in MODEL_BY_TENET:
        if tenet in tenets:
            return model
    doctrine = await ctx.session.get(CultDoctrineRow, cult_id)
    return AfterlifeModel.OBLIVION if doctrine is not None and doctrine.judgement is JudgementDoctrine.NONE else AfterlifeModel.JUDGED_REALMS


async def teach_afterlives(ctx: TickContext, tally: RiteTally) -> None:
    known = set(await ctx.session.scalars(select(DoctrineAfterlifeRow.cult_entity_id)))
    for cult_id in await churches(ctx):
        if cult_id in known or held(cult_id):
            continue
        ctx.session.add(DoctrineAfterlifeRow(cult_entity_id=cult_id, model=await taught_model(ctx, cult_id), updated_epoch=ctx.epoch, locked=[]))
        tally.afterlives += 1
    await ctx.session.flush()


async def model_of(ctx: TickContext, profile: SpiritProfileRow) -> AfterlifeModel | None:
    if profile.stratum_id is not None:
        stratum = await ctx.session.get(AfterlifeStratumRow, profile.stratum_id)
        if stratum is not None:
            return STRATUM_MODELS[stratum.kind]
    return STATE_MODELS.get(profile.state) if profile.state not in {AfterlifeState.JUDGED, AfterlifeState.IN_REALM} else None


async def met_this_epoch(ctx: TickContext) -> list[tuple[int, int, AfterlifeModel]]:
    found: list[tuple[int, int, AfterlifeModel]] = []
    judged = await ctx.session.scalars(select(SoulJudgementRow.spirit_entity_id).where(SoulJudgementRow.epoch == ctx.epoch).order_by(SoulJudgementRow.id))
    for spirit_id in dict.fromkeys(judged):
        profile = await ctx.session.get(SpiritProfileRow, spirit_id)
        model = await model_of(ctx, profile) if profile is not None else None
        if profile is not None and model is not None and profile.origin_mortal_id is not None:
            found.append((spirit_id, profile.origin_mortal_id, model))
    reborn = await ctx.session.execute(
        select(ReincarnationRow.spirit_entity_id, ReincarnationRow.past_mortal_id).where(ReincarnationRow.epoch == ctx.epoch).order_by(ReincarnationRow.id)
    )
    found.extend((spirit_id, mortal_id, AfterlifeModel.REBIRTH) for spirit_id, mortal_id in reborn if mortal_id is not None)
    wandering = await ctx.session.execute(
        select(SpiritProfileRow.spirit_entity_id, SpiritProfileRow.origin_mortal_id)
        .join(EntityRow, EntityRow.id == SpiritProfileRow.spirit_entity_id)
        .where(EntityRow.birth_epoch == ctx.epoch, SpiritProfileRow.state == AfterlifeState.WANDERING, SpiritProfileRow.origin_mortal_id.is_not(None))
        .order_by(SpiritProfileRow.spirit_entity_id)
    )
    found.extend((spirit_id, mortal_id, AfterlifeModel.WANDERING) for spirit_id, mortal_id in wandering if mortal_id is not None)
    return found


async def taught_to(ctx: TickContext, mortal_id: int) -> DoctrineAfterlifeRow | None:
    mortal = await ctx.session.get(EntityRow, mortal_id)
    town = await town_of(ctx.session, mortal) if mortal is not None else None
    cult = await church_of(ctx.session, town) if town is not None else None
    return await ctx.session.get(DoctrineAfterlifeRow, cult.id) if cult is not None else None


async def testify(ctx: TickContext, doctrine: DoctrineAfterlifeRow, count: int, tally: RiteTally) -> None:
    if count <= 0 or held(doctrine.cult_entity_id):
        return
    doctrine.testimonies += count
    if "doubt" not in doctrine.locked:
        doctrine.doubt = clamp_int(doctrine.doubt + count * ctx.rules.afterlife_belief.testimony_doubt, 0, PERCENT)
    tally.testimonies += count


async def shock_souls(ctx: TickContext, tally: RiteTally) -> None:
    table = ctx.rules.afterlife_belief
    for spirit_id, mortal_id, actual in await met_this_epoch(ctx):
        doctrine = await taught_to(ctx, mortal_id)
        if doctrine is None or doctrine.aligned or doctrine.model is actual or held(doctrine.cult_entity_id):
            continue
        spirit = await living_entity(ctx.session, spirit_id)
        if spirit is not None and not held(spirit.id):
            set_stats(spirit, unrest=clamp_int(stat_or(spirit, "unrest", 0) + table.shock_unrest, 0, PERCENT))
        doctrine.shocks += 1
        tally.shocks += 1
        if actual is AfterlifeModel.WANDERING:
            await testify(ctx, doctrine, 1, tally)


async def hear_the_dead(ctx: TickContext, tally: RiteTally) -> None:
    rows = await ctx.session.execute(
        select(DreamRow.dreamer_node_id, DreamRow.sender_node_id).where(
            DreamRow.epoch == ctx.epoch, DreamRow.kind == DreamKind.VISITATION, DreamRow.sender_node_id.is_not(None)
        )
    )
    for dreamer_id, sender_id in rows:
        profile = await ctx.session.get(SpiritProfileRow, sender_id)
        actual = await model_of(ctx, profile) if profile is not None else None
        doctrine = await taught_to(ctx, dreamer_id)
        if actual is None or doctrine is None or doctrine.model is actual:
            continue
        await testify(ctx, doctrine, 1, tally)


async def weigh_doubt(ctx: TickContext) -> None:
    table = ctx.rules.afterlife_belief
    for doctrine in await ctx.session.scalars(select(DoctrineAfterlifeRow).order_by(DoctrineAfterlifeRow.cult_entity_id)):
        if held(doctrine.cult_entity_id):
            continue
        if doctrine.doubt >= table.doubt_at:
            church = await ctx.session.get(CultDoctrineRow, doctrine.cult_entity_id)
            if church is not None and "orthodoxy" not in church.locked:
                church.orthodoxy = max(0, church.orthodoxy - table.doubt_orthodoxy)
        if "doubt" not in doctrine.locked:
            doctrine.doubt = max(0, doctrine.doubt - table.doubt_decay)
        doctrine.updated_epoch = ctx.epoch


async def keep_afterlife_belief(ctx: TickContext, tally: RiteTally) -> None:
    await teach_afterlives(ctx, tally)
    await shock_souls(ctx, tally)
    await hear_the_dead(ctx, tally)
    await weigh_doubt(ctx)


async def climate_of(ctx: TickContext, town_id: int) -> FaithClimateRow:
    row = await ctx.session.get(FaithClimateRow, town_id)
    if row is None:
        row = FaithClimateRow(community_entity_id=town_id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


def put(row: FaithClimateRow, key: str, value: int) -> None:
    if key not in row.locked:
        setattr(row, key, clamp_int(value, -PERCENT, PERCENT))


async def sound_theories(ctx: TickContext) -> dict[int, int]:
    rows = await ctx.session.execute(
        select(EntityRow.world_id, func.count())
        .join(TheoryProfileRow, TheoryProfileRow.theory_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, TheoryProfileRow.correctness >= MIDDLE)
        .group_by(EntityRow.world_id)
    )
    return {world: int(count) for world, count in rows if world is not None}


async def weigh_town(ctx: TickContext, town: EntityRow, signs: tuple[dict[int, int], set[int], dict[int, set[int]]]) -> FaithClimateRow:
    table = ctx.rules.secularisation
    theories, struck, miracles = signs
    row = await climate_of(ctx, town.id)
    people = await people_of(ctx.session, town)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    region = await region_of(ctx.session, town)
    wonders = len(miracles.get(region.id, set())) if region is not None else 0
    if "silent_epochs" not in row.locked:
        row.silent_epochs = 0 if wonders else row.silent_epochs + 1
    realm = await realm_of_town(ctx.session, town.id)
    put(row, "literacy_pull", -round_half_up((culture.literacy if culture is not None else 0) * table.literacy_pct / PERCENT))
    put(row, "science_pull", -min(table.science_cap, theories.get(town.world_id or 0, 0) * table.science_per_theory))
    put(row, "prosperity_pull", -round_half_up(max(0, stat_or(town, "prosperity", 0) - MIDDLE) * table.prosperity_pct / PERCENT))
    put(row, "city_pull", -min(CITY_CAP, stat_or(town, "population", 0) // max(1, table.city_scale)))
    church = await church_of(ctx.session, town)
    unseen = church is not None and await ctx.session.get(CultTenetRow, (church.id, TenetKind.HIDDEN_GOD)) is not None
    silence = min(table.silence_cap, row.silent_epochs * table.silence_per_epoch)
    put(row, "silence_pull", -round_half_up(silence * (PERCENT - table.hidden_god_pct) / PERCENT if unseen else silence))
    put(row, "disaster_push", table.disaster_push if region is not None and region.id in struck else 0)
    put(row, "miracle_push", wonders * table.miracle_push)
    put(row, "war_push", table.war_push if realm is not None and await ongoing_wars(ctx.session, realm) else 0)
    put(row, "dominion_push", round_half_up((await dominion_over(ctx, region.id) if region is not None else 0) * table.dominion_pct / PERCENT))
    pulls = (row.literacy_pull, row.science_pull, row.prosperity_pull, row.city_pull, row.silence_pull)
    pushes = (row.disaster_push, row.miracle_push, row.war_push, row.dominion_push)
    hastened = await tech_factor(ctx.session, ctx.rules, town.id, EraChannel.SECULARISATION)
    put(row, "piety_drift", round_half_up((sum(pulls) * hastened + sum(pushes)) * table.drift_pct / PERCENT))
    row.updated_epoch = ctx.epoch
    return row


async def drift(ctx: TickContext, town: EntityRow, row: FaithClimateRow, tally: RiteTally) -> None:
    table = ctx.rules.secularisation
    piety = clamp_int(stat_or(town, "piety", 0) + row.piety_drift, 0, PERCENT)
    set_stats(town, piety=piety)
    if row.piety_drift:
        tally.drifted += 1
    if "godless" in row.locked:
        return
    patron = await patron_of(ctx, town.id)
    flagged = await has_flag(ctx.session, town.id, EntityFlag.GODLESS)
    if piety <= table.godless_piety and patron is None and not flagged:
        await add_flag(ctx.session, town.id, EntityFlag.GODLESS, ctx.epoch)
        row.godless = True
        tally.godless += 1
        await note(ctx, f"{town.name} stopped believing in any god.", key="sacred.godless", ids=[town.id])
    elif flagged and piety >= table.faithful_piety:
        await remove_flag(ctx.session, town.id, EntityFlag.GODLESS)
        row.godless = False
        tally.faithful += 1
    else:
        row.godless = flagged


async def keep_climates(ctx: TickContext, tally: RiteTally) -> None:
    signs = (await sound_theories(ctx), await struck_regions(ctx), await miracles_by_region(ctx, ctx.epoch))
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        row = await weigh_town(ctx, town, signs)
        await drift(ctx, town, row, tally)


async def keep_rites(ctx: TickContext, tally: RiteTally) -> None:
    await keep_sacraments(ctx, tally)
    await keep_afterlife_belief(ctx, tally)
    await keep_climates(ctx, tally)
    await ctx.session.flush()
