from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.diseases import TRADITION_NAMES
from aerona.constants.units import PERCENT
from aerona.db.tables.disease import EndemicDiseaseRow, ImmunityRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.routes import JourneyRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.travel import JourneyStatus
from aerona.domain.enums.war import SiegeStatus
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.emergence import WET, new_strain
from aerona.engine.disease.outbreaks import lethality_factor, spread_factor, tally
from aerona.engine.notes import note
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, fraction, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat

ENDEMIC_LOAD = 40


async def region_communities(ctx: TickContext, book: DiseaseBook, region_id: int) -> list[EntityRow]:
    found = []
    for entity_id in book.atlas.communities_in(region_id):
        entity = await living_entity(ctx.session, entity_id)
        if entity is not None and entity.status is EntityStatus.CANON and entity.entity_type in COMMUNITY_TYPES and (stat(entity, "population") or 0) > 0:
            found.append(entity)
    return found


async def linger(ctx: TickContext, book: DiseaseBook, outbreak: OutbreakRow, knowledge: KnowledgeMap) -> None:
    disease = book.diseases.get(outbreak.disease_entity_id)
    if disease is None:
        return
    table = ctx.rules.epidemiology
    effects = ctx.rules.intervention_effects
    communities = await region_communities(ctx, book, outbreak.region_entity_id)
    scale = outbreak.severity / ctx.rules.disasters.scale_divisor * table.waning_death_pct / PERCENT
    dead = 0
    for community in communities:
        rate = fraction(effects.plague_population_loss) * scale * lethality_factor(book, disease.id, [community], knowledge)
        before = stat(community, "population") or 0
        floor, _ = headcount_bounds(ctx.rules, community)
        after = max(floor, round_half_up(before * (1 - min(1.0, rate))))
        set_stats(community, population=after)
        dead += before - after
    profile = book.profiles.get(disease.id)
    lethality = profile.lethality if profile is not None else table.neutral_lethality
    tally(disease, outbreak, infected=round_half_up(dead * PERCENT / max(1, lethality)), dead=dead)


async def finish(ctx: TickContext, book: DiseaseBook, outbreak: OutbreakRow) -> None:
    table = ctx.rules.epidemiology
    outbreak.status = OutbreakStatus.ENDED
    outbreak.ended_epoch = ctx.epoch
    communities = await region_communities(ctx, book, outbreak.region_entity_id)
    people = sum(stat(community, "population") or 0 for community in communities)
    reached = min(1.0, outbreak.infected / max(1, people))
    for community in communities:
        rows = book.immunity.setdefault((community.id, outbreak.disease_entity_id), {})
        for band in AgeBand:
            row = rows.get(band)
            if row is None:
                row = ImmunityRow(
                    community_entity_id=community.id, disease_entity_id=outbreak.disease_entity_id, age_band=band, immune_pct=0, since_epoch=ctx.epoch
                )
                ctx.session.add(row)
                rows[band] = row
            row.immune_pct = clamp_int(max(row.immune_pct, reached * table.survivor_immunity_pct), 0, PERCENT)
            row.since_epoch = ctx.epoch
    ground = await ctx.session.get(RegionEnvironmentRow, outbreak.region_entity_id)
    fitting = ground is not None and (ground.wetland >= WET or ground.disease_load >= ENDEMIC_LOAD)
    if fitting and ctx.rng(f"endemic.{outbreak.id}").chance(table.endemic_chance):
        await make_endemic(ctx, book, outbreak.region_entity_id, outbreak.disease_entity_id)
    if outbreak.dead >= table.tradition_dead_min and communities:
        await plague_tradition(ctx, book, outbreak, max(communities, key=lambda item: (stat(item, "population") or 0, -item.id)))


async def make_endemic(ctx: TickContext, book: DiseaseBook, region_id: int, disease_id: int) -> EndemicDiseaseRow:
    table = ctx.rules.epidemiology
    rows = book.endemic.setdefault(region_id, [])
    row = next((item for item in rows if item.disease_entity_id == disease_id), None)
    if row is None:
        row = EndemicDiseaseRow(region_entity_id=region_id, disease_entity_id=disease_id, load=table.endemic_load, since_epoch=ctx.epoch)
        ctx.session.add(row)
        rows.append(row)
        disease = book.diseases.get(disease_id)
        region = await ctx.session.get(EntityRow, region_id)
        if disease is not None and region is not None:
            await note(
                ctx,
                f"{disease.name.capitalize()} never quite left {region.name}; it became a sickness of the land, and strangers now fear it.",
                key="disease.endemic",
                ids=[disease.id, region.id],
                feed=FeedCategory.DISASTER,
                kind=ChronicleKind.DISASTER,
            )
    else:
        row.load = clamp_int(row.load + table.endemic_load, 0, PERCENT)
    return row


async def plague_tradition(ctx: TickContext, book: DiseaseBook, outbreak: OutbreakRow, community: EntityRow) -> None:
    disease = book.diseases.get(outbreak.disease_entity_id)
    if disease is None:
        return
    name = ctx.rng(f"plague_tradition.{outbreak.id}").pick(TRADITION_NAMES)
    tradition = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.TRADITION,
            name=f"{name} of {community.name}",
            body=f"Kept by {community.name} in memory of the {outbreak.dead} who died of {disease.name}.",
            stats=TraditionStats(spread=20, rigidity=40),
            power=2,
            location_id=community.id,
            world_id=community.world_id,
            subtype="plague rite",
            pending=False,
        ),
    )
    await note(
        ctx,
        f"The survivors of {disease.name} in {community.name} began to keep {tradition.name}.",
        key="disease.tradition",
        ids=[tradition.id, community.id, disease.id],
        kind=ChronicleKind.WORLD,
    )


async def run_course(ctx: TickContext, book: DiseaseBook) -> None:
    table = ctx.rules.epidemiology
    knowledge = await KnowledgeMap.load(ctx.session)
    for outbreak in list(book.outbreaks):
        age = ctx.epoch - outbreak.started_epoch
        communities = await region_communities(ctx, book, outbreak.region_entity_id)
        people = sum(stat(item, "population") or 0 for item in communities)
        immune = sum(book.immune_share(item.id, outbreak.disease_entity_id) * (stat(item, "population") or 0) for item in communities) / max(1, people)
        if age <= 0:
            continue
        if outbreak.status is OutbreakStatus.WANING or immune >= book.herd_threshold(outbreak.disease_entity_id) or not communities:
            await finish(ctx, book, outbreak)
            ctx.count("outbreaks_ended")
            continue
        await linger(ctx, book, outbreak, knowledge)
        if age >= table.outbreak_epochs:
            outbreak.status = OutbreakStatus.WANING
    book.outbreaks = [item for item in book.outbreaks if item.status is not OutbreakStatus.ENDED]


def fade_immunity(ctx: TickContext, book: DiseaseBook) -> None:
    table = ctx.rules.epidemiology
    for (community_id, disease_id), rows in book.immunity.items():
        profile = book.profiles.get(disease_id)
        keep = 1 - 1 / max(1, profile.immunity_epochs if profile is not None else 1)
        region = book.atlas.top_region(community_id)
        endemic = next((row.load for row in book.endemic.get(region or -1, []) if row.disease_entity_id == disease_id), 0)
        for band, row in rows.items():
            kept = row.immune_pct * keep * (1 - table.child_immunity_loss_pct / PERCENT if band is AgeBand.CHILD else 1)
            row.immune_pct = clamp_int(max(kept, endemic if band is not AgeBand.CHILD else endemic / 2), 0, PERCENT)


async def settle_endemic(ctx: TickContext, book: DiseaseBook) -> None:
    table = ctx.rules.epidemiology
    renewed = {(item.region_entity_id, item.disease_entity_id) for item in book.outbreaks}
    for region_id, rows in list(book.endemic.items()):
        for row in list(rows):
            if (region_id, row.disease_entity_id) in renewed:
                continue
            row.load = max(0, row.load - table.endemic_decay)
            if row.load <= 0:
                await ctx.session.delete(row)
                rows.remove(row)
        for row in rows:
            for community_id in book.atlas.communities_in(region_id):
                if (community_id, row.disease_entity_id) not in book.immunity:
                    book.immunity[(community_id, row.disease_entity_id)] = {}
                    for band in AgeBand:
                        immune = ImmunityRow(
                            community_entity_id=community_id,
                            disease_entity_id=row.disease_entity_id,
                            age_band=band,
                            immune_pct=row.load if band is not AgeBand.CHILD else row.load // 2,
                            since_epoch=ctx.epoch,
                        )
                        ctx.session.add(immune)
                        book.immunity[(community_id, row.disease_entity_id)][band] = immune


async def mutate(ctx: TickContext, book: DiseaseBook) -> int:
    table = ctx.rules.epidemiology
    made = 0
    struck: dict[int, list[OutbreakRow]] = defaultdict(list)
    for outbreak in book.outbreaks:
        struck[outbreak.disease_entity_id].append(outbreak)
    for disease_id, outbreaks in sorted(struck.items()):
        if made >= table.mutation_cap:
            break
        disease = book.diseases.get(disease_id)
        profile = book.profiles.get(disease_id)
        if disease is None or profile is None:
            continue
        immune = [book.immune_share(community_id, disease_id) for (community_id, found) in book.immunity if found == disease_id]
        pressure = sum(immune) / len(immune) if immune else 0.0
        chance = profile.mutation_rate * (1 + pressure * table.mutation_immune_pct / PERCENT)
        if not ctx.rng(f"mutation.{disease_id}").chance(chance):
            continue
        home = max(outbreaks, key=lambda item: (item.infected, -item.id))
        region = await ctx.session.get(EntityRow, home.region_entity_id)
        if region is None:
            continue
        strain = await new_strain(ctx, book, disease, region)
        if strain is None:
            continue
        made += 1
        targets = await region_communities(ctx, book, region.id)
        if targets:
            target = max(targets, key=lambda item: (stat(item, "population") or 0, -item.id))
            await strike_plague(ctx, target, home.severity, disease=strain, path=SpreadPath.MUTATION, source=home)
        await note(
            ctx,
            f"In {region.name}, {disease.name} changed: {strain.name} struck even those who had survived the old sickness.",
            key="disease.strain",
            ids=[strain.id, disease.id, region.id],
            feed=FeedCategory.DISASTER,
            kind=ChronicleKind.DISASTER,
        )
    return made


async def carry_by_armies(ctx: TickContext, book: DiseaseBook) -> int:
    table = ctx.rules.epidemiology
    carried = 0
    rows = await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))
    for row in rows:
        army = await living_entity(ctx.session, row.entity_id)
        owner = await living_entity(ctx.session, row.owner_entity_id)
        if army is None or owner is None:
            continue
        here = book.atlas.top_region(army.id)
        home = book.atlas.top_region(owner.id)
        if here is None or here == home:
            continue
        for outbreak in book.outbreaks_in(here):
            disease = book.diseases.get(outbreak.disease_entity_id)
            if disease is None or book.active_of(disease.id, home) is not None:
                continue
            ground = await ctx.session.get(RegionEnvironmentRow, home) if home is not None else None
            chance = table.army_spread_chance * spread_factor(book, disease.id, owner, ground, source_region=here)
            if not ctx.rng(f"army_spread.{army.id}.{outbreak.id}").chance(min(PERCENT, chance)):
                continue
            await strike_plague(ctx, owner, outbreak.severity, disease=disease, path=SpreadPath.ARMY, source=outbreak)
            carried += 1
            await note(
                ctx,
                f"The soldiers of {army.name} came home from the sick lands, and {disease.name} came with them to {owner.name}.",
                key="disease.army_carried",
                ids=[army.id, owner.id, disease.id],
                feed=FeedCategory.DISASTER,
                kind=ChronicleKind.DISASTER,
            )
            break
    return carried


async def carry_by_journeys(ctx: TickContext, book: DiseaseBook) -> int:
    table = ctx.rules.epidemiology
    carried = 0
    rows = await ctx.session.scalars(
        select(JourneyRow).where(JourneyRow.status == JourneyStatus.ARRIVED, JourneyRow.end_epoch == ctx.epoch, JourneyRow.result_entity_id.is_not(None))
    )
    for journey in rows:
        traveller = await living_entity(ctx.session, journey.traveller_entity_id)
        landed = await living_entity(ctx.session, journey.result_entity_id) if journey.result_entity_id is not None else None
        if traveller is None or landed is None:
            continue
        origin = book.atlas.top_region(traveller.id)
        for outbreak in book.outbreaks_in(origin):
            disease = book.diseases.get(outbreak.disease_entity_id)
            if disease is None:
                continue
            ground = await ctx.session.get(RegionEnvironmentRow, book.atlas.top_region(landed.id) or -1)
            chance = table.journey_spread_chance * spread_factor(book, disease.id, landed, ground, source_region=origin)
            if not ctx.rng(f"journey_spread.{journey.id}.{outbreak.id}").chance(min(PERCENT, chance)):
                continue
            await strike_plague(ctx, landed, outbreak.severity, disease=disease, path=SpreadPath.JOURNEY, source=outbreak)
            carried += 1
            break
    return carried


async def camp_disease(ctx: TickContext, book: DiseaseBook) -> int:
    table = ctx.rules.epidemiology
    lost = 0
    sieges = await ctx.session.scalars(select(SiegeRow).where(SiegeRow.status == SiegeStatus.ONGOING).order_by(SiegeRow.id))
    besieging: dict[int, int] = {}
    for siege in sieges:
        region = book.atlas.top_region(siege.besieged_entity_id)
        if region is not None:
            besieging[siege.besieger_entity_id] = region
    rows = await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))
    for row in rows:
        army = await living_entity(ctx.session, row.entity_id)
        if army is None:
            continue
        size = stat(army, "size") or 0
        if size <= 0:
            continue
        here = book.atlas.top_region(army.id)
        share = 0.0
        siege_region = besieging.get(row.owner_entity_id)
        if siege_region is not None:
            ground = await ctx.session.get(RegionEnvironmentRow, siege_region)
            load = (
                (ground.disease_load if ground is not None else 0)
                + book.endemic_load(siege_region)
                + sum(item.severity for item in book.outbreaks_in(siege_region)) // 2
            )
            share += table.siege_attrition_pct / PERCENT * min(PERCENT, load) / PERCENT
        for endemic in book.endemic.get(here or -1, []):
            if not book.met_before(row.owner_entity_id, endemic.disease_entity_id):
                share += table.foreign_army_attrition_pct / PERCENT * endemic.load / PERCENT
        if share <= 0:
            continue
        losses = min(size, round_half_up(size * min(1.0, share)))
        if losses <= 0:
            continue
        set_stats(army, size=size - losses)
        lost += losses
    return lost
